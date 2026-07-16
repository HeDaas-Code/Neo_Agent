"""
情感关系分析模块
初次评估基于前5轮对话，后续每15轮对话更新评估
使用LLM生成对用户的印象并进行累加评分
使用数据库替代JSON文件存储

P2 增强：
- 新增 PlutchikEmotionWheel（8 基本情绪 + 衰减 + profile 推导）
- 累加评分（EmotionRelationshipAnalyzer）作为"关系状态"维度保留
- PlutchikEmotionWheel 作为"当下情绪"维度补充
- 二者并行注入 prompt，由 chat_agent 协调
"""

import os
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from src.core.database_manager import DatabaseManager
from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()

ENABLE_EMOTION_WHEEL = os.getenv('ENABLE_EMOTION_WHEEL', 'false').lower() == 'true'


class EmotionRelationshipAnalyzer:
    """
    情感关系分析器
    分阶段评估系统：
    - 初次评估：基于前5轮对话，生成初始印象并评分(0-35)
    - 更新评估：每15轮对话，评估最近表现并给出分数变化(-3到+3)
    使用累加评分系统，基于角色设定生成印象
    使用数据库存储替代JSON文件
    """

    def __init__(self,
                 db_manager: DatabaseManager = None):
        """
        初始化情感关系分析器（使用LangChain架构）

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()
        
        # 初始化模型名称（用于日志记录）
        self.model_name = os.getenv('TOOL_MODEL_NAME', 'zai-org/GLM-4.6V')

        # 检查是否需要从JSON迁移数据
        if os.path.exists('emotion_data.json'):
            print("○ 检测到旧的情感数据JSON文件，正在迁移...")
            self._migrate_from_json('emotion_data.json')
            os.rename('emotion_data.json', 'emotion_data.json.bak')
            print("✓ 情感数据已迁移，JSON文件已备份")

        print("✓ 情感关系分析器已初始化（使用数据库存储，基于LangChain）")

    def analyze_emotion_relationship(self,
                                    messages: List[Dict[str, str]],
                                    character_name: str = "AI",
                                    character_settings: str = "",
                                    is_initial: bool = None) -> Dict[str, Any]:
        """
        分析情感关系（累加评分系统）

        Args:
            messages: 对话消息列表
            character_name: AI角色名称
            character_settings: 角色设定描述
            is_initial: 是否为初次评估，None表示自动判断

        Returns:
            情感分析结果，包含印象评分和描述
        """
        debug_logger.log_module('EmotionAnalyzer', '开始情感关系分析', {
            'total_messages': len(messages),
            'character_name': character_name
        })

        # 获取历史评分
        latest_emotion = self.get_latest_emotion()
        current_score = latest_emotion.get('overall_score', 0) if latest_emotion else 0
        
        # 自动判断是初次评估还是更新评估：仅根据是否存在历史情感记录
        if is_initial is None:
            is_initial = (latest_emotion is None)
        
        # 根据评估类型选择分析的对话轮数
        if is_initial:
            # 初次评估：使用前5轮对话（10条消息）
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            min_messages = 2
        else:
            # 更新评估：使用最近15轮对话（30条消息）
            recent_messages = messages[-30:] if len(messages) > 30 else messages
            min_messages = 2

        if len(recent_messages) < min_messages:
            # 对话太少，返回默认值
            debug_logger.log_info('EmotionAnalyzer', '对话数量不足，返回默认情感数据', {
                'message_count': len(recent_messages)
            })
            return self._get_default_emotion_result()

        # 构建分析提示词
        conversation_text = self._format_conversation(recent_messages)
        prompt = self._build_analysis_prompt(
            conversation_text, 
            character_name, 
            character_settings,
            is_initial=is_initial,
            current_score=current_score
        )

        debug_logger.log_prompt('EmotionAnalyzer', 'user', prompt, {
            'message_count': len(recent_messages),
            'prompt_length': len(prompt)
        })

        try:
            # 调用LLM进行分析
            debug_logger.log_info('EmotionAnalyzer', '调用LLM进行情感分析', {
                'model': self.model_name
            })

            result = self._call_llm(prompt)

            debug_logger.log_info('EmotionAnalyzer', 'LLM返回结果', {
                'result_length': len(result)
            })

            # 解析结果
            emotion_data = self._parse_emotion_result(result, is_initial=is_initial)
            
            # 处理累加评分
            if is_initial:
                # 初次评估：使用返回的分数作为初始分数，并确保在0-35范围内
                final_score = max(0, min(35, emotion_data.get('overall_score', 0)))
                emotion_data['overall_score'] = final_score
                debug_logger.log_info('EmotionAnalyzer', '初次评估', {
                    'initial_score': final_score
                })
            else:
                # 更新评估：当前分数 + 变化量，并确保变化量在-3到+3范围内
                score_change = emotion_data.get('score_change', 0)
                score_change = max(-3, min(3, score_change))
                final_score = current_score + score_change
                # 确保分数在合理范围内（0-100）
                final_score = max(0, min(100, final_score))
                emotion_data['overall_score'] = final_score
                emotion_data['previous_score'] = current_score
                emotion_data['score_change'] = score_change
                debug_logger.log_info('EmotionAnalyzer', '更新评估', {
                    'previous_score': current_score,
                    'score_change': score_change,
                    'final_score': final_score
                })

            # 添加时间戳
            emotion_data['timestamp'] = datetime.now().isoformat()
            emotion_data['message_count'] = len(recent_messages)
            emotion_data['is_initial'] = is_initial

            # 保存到数据库
            self._save_emotion_to_db(emotion_data)

            debug_logger.log_info('EmotionAnalyzer', '情感分析完成', {
                'overall_score': emotion_data.get('overall_score', 0),
                'relationship_type': emotion_data.get('relationship_type', '未知'),
                'emotional_tone': emotion_data.get('emotional_tone', '未知')
            })

            return emotion_data

        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'情感分析时出错: {str(e)}', e)
            print(f"情感分析时出错: {e}")
            return self._get_default_emotion_result()

    def _save_emotion_to_db(self, emotion_data: Dict[str, Any]):
        """
        保存情感分析结果到数据库

        Args:
            emotion_data: 情感分析数据
        """
        try:
            # 安全地将评分字段转换为整数，避免类型错误
            def _safe_int(value, default=0):
                try:
                    if value is None:
                        return default
                    return int(value)
                except (TypeError, ValueError):
                    return default

            # 将印象和分析合并到analysis_summary中
            impression = emotion_data.get('impression', '')
            analysis = emotion_data.get('analysis', '')
            is_initial = emotion_data.get('is_initial', False)
            
            # 统一规范 overall_score，确保用于摘要和数据库时一致
            overall_score = _safe_int(emotion_data.get('overall_score'), 0)
            
            # 添加评分信息到摘要
            if is_initial:
                score_info = f"【初始评分】{overall_score}/35\n\n"
            else:
                score_change = _safe_int(emotion_data.get('score_change'), None)
                previous_score = _safe_int(emotion_data.get('previous_score'), None)
                
                if score_change is None or previous_score is None:
                    # 评分变化信息不完整或无效，降级为仅展示当前评分
                    debug_logger.log_error(
                        'EmotionAnalyzer',
                        '情感数据缺少或包含无效的评分变化字段，已降级为仅当前评分摘要'
                    )
                    score_info = f"【当前评分】{overall_score}/100\n\n"
                else:
                    score_info = f"【评分变化】{previous_score} → {overall_score} ({score_change:+d})\n\n"
            
            combined_summary = f"{score_info}【印象】\n{impression}\n\n【总结】\n{analysis}"
            
            self.db.add_emotion_analysis(
                relationship_type=emotion_data.get('relationship_type', '未知'),
                emotional_tone=emotion_data.get('emotional_tone', '未知'),
                overall_score=overall_score,
                intimacy=0,  # 不再使用维度评分
                trust=0,
                pleasure=0,
                resonance=0,
                dependence=0,
                analysis_summary=combined_summary
            )
            debug_logger.log_info('EmotionAnalyzer', '情感数据已保存到数据库')
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'保存情感数据失败: {str(e)}', e)
            print(f"✗ 保存情感数据到数据库时出错: {e}")

    def _migrate_from_json(self, json_file: str):
        """
        从JSON文件迁移情感数据到数据库

        Args:
            json_file: JSON文件路径
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                emotion_history = json.load(f)

            count = 0
            for emotion_data in emotion_history:
                try:
                    self.db.add_emotion_analysis(
                        relationship_type=emotion_data.get('relationship_type', '未知'),
                        emotional_tone=emotion_data.get('emotional_tone', '未知'),
                        overall_score=emotion_data.get('overall_score', 0),
                        intimacy=emotion_data.get('亲密度', 0),
                        trust=emotion_data.get('信任度', 0),
                        pleasure=emotion_data.get('愉悦度', 0),
                        resonance=emotion_data.get('共鸣度', 0),
                        dependence=emotion_data.get('依赖度', 0),
                        analysis_summary=emotion_data.get('analysis', '')
                    )
                    count += 1
                except Exception as e:
                    print(f"✗ 迁移情感数据条目失败: {e}")

            print(f"✓ 迁移情感数据: {count}/{len(emotion_history)} 条")
        except Exception as e:
            print(f"✗ 从JSON迁移情感数据失败: {e}")

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        格式化对话内容

        Args:
            messages: 消息列表

        Returns:
            格式化后的对话文本
        """
        formatted = []
        for msg in messages:
            role = "用户" if msg['role'] == 'user' else "AI"
            content = msg['content']
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    def _build_analysis_prompt(self, conversation_text: str, character_name: str, 
                               character_settings: str = "", is_initial: bool = True,
                               current_score: int = 0) -> str:
        """
        构建情感分析提示词（使用提示词模板）

        Args:
            conversation_text: 对话文本
            character_name: AI角色名称
            character_settings: 角色设定描述
            is_initial: 是否为初次评估
            current_score: 当前累计分数

        Returns:
            分析提示词
        """
        try:
            from src.core.prompt_manager import get_prompt_manager
            prompt_manager = get_prompt_manager()
            
            # 准备变量
            analysis_type = "初次评估" if is_initial else "更新评估"
            variables = {
                'character_name': character_name,
                'character_settings': character_settings or "无特殊设定",
                'analysis_type': analysis_type,
                'conversation_text': conversation_text,
                'current_score': current_score
            }
            
            # 加载并渲染模板
            prompt = prompt_manager.get_system_prompt('emotion_analysis', variables)
            
            # 根据评估类型附加具体指令
            if is_initial:
                prompt += f"""

【当前任务】
这是初次评估，基于前5轮对话。

对话内容：
{conversation_text}

请返回JSON格式的初次评估结果。"""
            else:
                prompt += f"""

【当前任务】
这是更新评估，基于最近15轮对话。
当前累计分数：{current_score}/100

最近对话内容：
{conversation_text}

请返回JSON格式的更新评估结果。"""
            
            return prompt
            
        except Exception as e:
            # 如果模板加载失败，使用后备的硬编码提示词
            debug_logger.log_error('EmotionAnalyzer', f'加载提示词模板失败: {str(e)}', e)
            return self._build_fallback_prompt(conversation_text, character_name, 
                                             character_settings, is_initial, current_score)

    def _build_fallback_prompt(self, conversation_text: str, character_name: str, 
                               character_settings: str = "", is_initial: bool = True,
                               current_score: int = 0) -> str:
        """
        后备的硬编码提示词（兼容性）

        Args:
            conversation_text: 对话文本
            character_name: AI角色名称
            character_settings: 角色设定描述
            is_initial: 是否为初次评估
            current_score: 当前累计分数

        Returns:
            分析提示词
        """
        character_context = f"\n角色设定：\n{character_settings}\n" if character_settings else ""
        
        if is_initial:
            # 初次评估提示词
            prompt = f"""你是AI角色"{character_name}"，这是你和用户的初次见面。请基于你的角色设定和最近5轮对话，生成你对用户的初步印象。
{character_context}
对话内容：
{conversation_text}

请基于你的角色性格和对话内容，完成以下任务：
1. 生成你对用户的初步印象（150-200字），包括：
   - 用户的第一印象
   - 用户的态度和表现
   - 对这次初识的感受
   
2. 给出初始情感评分（0-35分）：
   - 0-10分：非常负面的初印象（用户冷淡、敌对、无礼等）
   - 11-20分：较负面的初印象（用户不够友好、态度消极等）
   - 21-28分：中性初印象（普通的开始，无明显特点）
   - 29-32分：较正面的初印象（用户友好、有礼貌等）
   - 33-35分：非常正面的初印象（用户热情、真诚、令人愉快等）

3. 概括关系类型和情感基调

请以JSON格式返回分析结果，格式如下：
{{
    "impression": "对用户的初步印象描述",
    "overall_score": 初始评分(0-35),
    "sentiment": "印象倾向(positive/neutral/negative)",
    "relationship_type": "关系类型(如：初识、陌生人等)",
    "emotional_tone": "整体情感基调(如：积极、中性、消极)",
    "key_topics": ["主要话题1", "主要话题2"],
    "analysis": "简短的关系总结(50字以内)"
}}

只返回JSON，不要有其他内容。"""
        else:
            # 更新评估提示词
            prompt = f"""你是AI角色"{character_name}"，你们已经有过一些交流了。请基于你的角色设定和最近15轮对话，更新你对用户的印象。
{character_context}
当前累计情感分数：{current_score}/100

最近对话内容：
{conversation_text}

请基于你的角色性格和最近的对话内容，完成以下任务：
1. 生成对最近交流的印象评价（150-200字），包括：
   - 用户在最近对话中的表现
   - 相比之前的变化或延续
   - 对最近交流的感受
   
2. 根据最近对话的印象，给出分数变化（-3到+3分）：
   - -3分：最近表现很差（态度恶化、不尊重、冷漠等）
   - -2分：表现较差（不够友好、兴趣降低等）
   - -1分：略有不足（小问题、轻微不愉快等）
   - 0分：保持现状（无明显变化）
   - +1分：略有改善（更友好、更积极等）
   - +2分：表现较好（明显改善、增进了解等）
   - +3分：表现很好（大幅改善、深入交流、建立信任等）

3. 更新关系类型和情感基调

请以JSON格式返回分析结果，格式如下：
{{
    "impression": "对最近交流的印象评价",
    "score_change": 分数变化(-3到+3),
    "sentiment": "印象倾向(positive/neutral/negative)",
    "relationship_type": "更新后的关系类型",
    "emotional_tone": "整体情感基调",
    "key_topics": ["主要话题1", "主要话题2"],
    "analysis": "简短的变化总结(50字以内)"
}}

只返回JSON，不要有其他内容。"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API（使用工具模型处理情感分析任务）

        Args:
            prompt: 提示词

        Returns:
            LLM返回的文本
        """
        from src.core.llm_helper import LLMHelper
        
        debug_logger.log_info('EmotionAnalyzer', '调用工具模型进行情感分析')
        
        try:
            # 使用工具模型处理情感分析（轻量级任务）
            response = LLMHelper.call_tool_model(
                system_prompt="你是一个情感分析专家，负责分析对话中的情感关系。",
                user_message=prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            debug_logger.log_info('EmotionAnalyzer', 'LLM调用成功', {
                'response_length': len(response)
            })
            
            return response
            
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'LLM调用异常: {str(e)}', e)
            raise

    def _parse_emotion_result(self, result_text: str, is_initial: bool = True) -> Dict[str, Any]:
        """
        解析LLM返回的情感分析结果

        Args:
            result_text: LLM返回的文本
            is_initial: 是否为初次评估

        Returns:
            解析后的情感数据
        """
        debug_logger.log_info('EmotionAnalyzer', '开始解析LLM返回结果', {
            'result_length': len(result_text),
            'is_initial': is_initial
        })

        try:
            # 尝试提取JSON部分
            result_text = result_text.strip()

            # 如果有markdown代码块，去除
            if result_text.startswith('```'):
                debug_logger.log_info('EmotionAnalyzer', '检测到markdown代码块，正在清理')
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
                if result_text.startswith('json'):
                    result_text = result_text[4:].strip()

            # 解析JSON
            emotion_data = json.loads(result_text)

            debug_logger.log_info('EmotionAnalyzer', 'JSON解析成功', {
                'keys': list(emotion_data.keys())
            })

            # 确保所有必需字段存在
            if is_initial:
                required_fields = {
                    "impression": "暂无印象描述",
                    "overall_score": 15,  # 初次评估默认中间值
                    "sentiment": "neutral",
                    "relationship_type": "初识",
                    "emotional_tone": "中性",
                    "key_topics": [],
                    "analysis": "暂无分析"
                }
            else:
                required_fields = {
                    "impression": "暂无印象描述",
                    "score_change": 0,  # 更新评估默认无变化
                    "sentiment": "neutral",
                    "relationship_type": "普通朋友",
                    "emotional_tone": "中性",
                    "key_topics": [],
                    "analysis": "暂无分析"
                }

            missing_fields = []
            for field, default_value in required_fields.items():
                if field not in emotion_data:
                    emotion_data[field] = default_value
                    missing_fields.append(field)

            if missing_fields:
                debug_logger.log_info('EmotionAnalyzer', '补充缺失字段', {
                    'missing_fields': missing_fields
                })

            return emotion_data

        except json.JSONDecodeError as e:
            debug_logger.log_error('EmotionAnalyzer', f'JSON解析失败: {str(e)}', e)
            debug_logger.log_info('EmotionAnalyzer', '原始结果内容', {
                'result_text': result_text[:500]  # 只记录前500字符
            })
            print(f"解析情感结果时出错: {e}")
            print(f"原始结果: {result_text}")
            return self._get_default_emotion_result(is_initial)
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'解析情感结果时出错: {str(e)}', e)
            print(f"解析情感结果时出错: {e}")
            print(f"原始结果: {result_text}")
            return self._get_default_emotion_result(is_initial)

    def _get_default_emotion_result(self, is_initial: bool = True) -> Dict[str, Any]:
        """
        获取默认情感分析结果

        Args:
            is_initial: 是否为初次评估

        Returns:
            默认情感数据
        """
        base_result = {
            "impression": "对话轮数较少，尚未形成明确印象。用户表现正常，期待更多交流。",
            "relationship_type": "初识",
            "emotional_tone": "中性",
            "key_topics": [],
            "analysis": "对话刚开始，关系尚在建立初期。",
            "timestamp": datetime.now().isoformat(),
            "message_count": 0,
            "is_initial": is_initial,
            "sentiment": "neutral"
        }
        
        if is_initial:
            base_result["overall_score"] = 15  # 默认初始分数中间值
        else:
            base_result["score_change"] = 0  # 默认无变化
            base_result["overall_score"] = 0
            base_result["previous_score"] = 0
        
        return base_result

    def get_emotion_trend(self) -> List[Dict[str, Any]]:
        """
        获取情感关系变化趋势（从数据库）

        Returns:
            历史情感数据列表
        """
        emotion_history = self.db.get_emotion_history()

        # 转换为新格式
        result = []
        for emotion in emotion_history:
            analysis_summary = emotion.get('analysis_summary', '')
            # 尝试分离印象和总结
            impression = ""
            analysis = ""
            if "【印象】" in analysis_summary and "【总结】" in analysis_summary:
                # 先移除可能存在的评分前缀行（如【初始评分】或【评分变化】）
                cleaned_lines = []
                for line in analysis_summary.splitlines():
                    if line.startswith("【初始评分】") or line.startswith("【评分变化】") or line.startswith("【当前评分】"):
                        continue
                    cleaned_lines.append(line)
                cleaned_summary = "\n".join(cleaned_lines).lstrip()
                
                parts = cleaned_summary.split("【总结】", 1)
                impression = parts[0].replace("【印象】", "").strip()
                analysis = parts[1].strip() if len(parts) > 1 else ""
            else:
                # 旧格式或简单格式
                analysis = analysis_summary
                impression = "暂无详细印象"
            
            result.append({
                "impression": impression,
                "overall_score": emotion.get('overall_score', 0),
                "sentiment": self._score_to_sentiment(emotion.get('overall_score', 50)),
                "relationship_type": emotion.get('relationship_type', '未知'),
                "emotional_tone": emotion.get('emotional_tone', '未知'),
                "analysis": analysis,
                "timestamp": emotion.get('created_at', ''),
                "uuid": emotion.get('uuid', '')
            })

        return result
    
    def _score_to_sentiment(self, score: int) -> str:
        """
        将评分转换为情感倾向
        
        Args:
            score: 评分值，可以是 0-100 或 0-35 的评分
            
        Returns:
            情感倾向：positive/neutral/negative
        """
        # 处理空值，避免异常
        if score is None:
            return "neutral"

        # 如果评分在 0-35 之间，认为是初始评估的 0-35 制分数，先归一化到 0-100
        if 0 <= score <= 35:
            normalized_score = round(score / 35 * 100)
        else:
            normalized_score = score

        # 简单限制范围，防止异常值影响结果
        if normalized_score < 0:
            normalized_score = 0
        elif normalized_score > 100:
            normalized_score = 100

        if normalized_score >= 61:
            return "positive"
        elif normalized_score >= 41:
            return "neutral"
        else:
            return "negative"

    def get_latest_emotion(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的情感分析结果（从数据库）

        Returns:
            最新情感数据，如果没有则返回None
        """
        latest = self.db.get_latest_emotion()

        if not latest:
            return None

        # 转换为新格式
        analysis_summary = latest.get('analysis_summary', '')
        impression = ""
        analysis = ""
        if "【印象】" in analysis_summary and "【总结】" in analysis_summary:
            # 先移除可能存在的评分前缀行（如【初始评分】或【评分变化】）
            cleaned_lines = []
            for line in analysis_summary.splitlines():
                if line.startswith("【初始评分】") or line.startswith("【评分变化】") or line.startswith("【当前评分】"):
                    continue
                cleaned_lines.append(line)
            cleaned_summary = "\n".join(cleaned_lines).lstrip()
            
            parts = cleaned_summary.split("【总结】", 1)
            impression = parts[0].replace("【印象】", "").strip()
            analysis = parts[1].strip() if len(parts) > 1 else ""
        else:
            # 旧格式或简单格式
            analysis = analysis_summary
            impression = "暂无详细印象"
        
        return {
            "impression": impression,
            "overall_score": latest.get('overall_score', 0),
            "sentiment": self._score_to_sentiment(latest.get('overall_score', 50)),
            "relationship_type": latest.get('relationship_type', '未知'),
            "emotional_tone": latest.get('emotional_tone', '未知'),
            "analysis": analysis,
            "timestamp": latest.get('created_at', ''),
            "uuid": latest.get('uuid', '')
        }

    # ==================== Stage B.3 Web 后端兼容接口 ====================

    # Plutchik 8 维情绪键（与 PlutchikEmotionWheel 保持一致）
    PLUTCHIK_KEYS = (
        'joy', 'trust', 'fear', 'surprise',
        'sadness', 'disgust', 'anger', 'anticipation',
    )
    PLUTCHIK_CN = {
        'joy': '喜悦', 'trust': '信任', 'fear': '恐惧', 'surprise': '惊讶',
        'sadness': '悲伤', 'disgust': '厌恶', 'anger': '愤怒', 'anticipation': '期待',
    }

    def _derive_plutchik_from_legacy(
        self, overall_score: int, emotional_tone: str,
    ) -> Dict[str, float]:
        """
        从旧的累加评分（overall_score）+ emotional_tone 推导 Plutchik 8 维（0-1）。

        用于 Stage B.3: 在 emotion_history 表未存 Plutchik 原始数据时，
        提供合理的可视化默认值；不修改现有 emotion_history 表 schema。
        """
        try:
            score = float(overall_score or 0)
        except (TypeError, ValueError):
            score = 0.0
        # 0-35 视作初始评估制，先归一到 0-100
        if 0.0 <= score <= 35.0:
            score = score / 35.0 * 100.0
        score = max(0.0, min(100.0, score))
        norm = score / 100.0  # 0-1 基础强度

        tone = (emotional_tone or '中性').strip()
        # 默认 8 维分配：积极高 / 消极低 / 中性均匀
        base = {
            'joy': 0.3, 'trust': 0.3, 'fear': 0.1, 'surprise': 0.1,
            'sadness': 0.1, 'disgust': 0.1, 'anger': 0.1, 'anticipation': 0.3,
        }
        if tone in ('积极', '正面', '乐观'):
            base.update({
                'joy': 0.6, 'trust': 0.6, 'anticipation': 0.5,
                'fear': 0.05, 'sadness': 0.05, 'disgust': 0.05, 'anger': 0.05,
            })
        elif tone in ('消极', '负面', '悲观'):
            base.update({
                'joy': 0.1, 'trust': 0.2, 'anticipation': 0.1,
                'fear': 0.5, 'sadness': 0.6, 'disgust': 0.4, 'anger': 0.5,
            })
        else:  # 中性 / 未知
            for k in base:
                base[k] = 0.2 + 0.1 * norm

        # 用 norm 缩放（高分 → 整体更强）
        scale = 0.5 + 0.5 * norm
        out = {k: max(0.0, min(1.0, float(v) * scale)) for k, v in base.items()}
        return out

    def get_latest_for_user(self, user_id: str = "default") -> Dict[str, Any]:
        """
        获取指定用户的最新情感数据（Web 后端专用）。

        返回结构（对齐前端 EmotionPanel.tsx + Pydantic EmotionLatestResponse）：
        - timestamp: ISO 8601 字符串
        - additive_scores: Plutchik 8 维累加评分（dict，每维 0-100）
        - plutchik: Plutchik 8 维强度（dict，每维 0-1）
        - dominant: 主导情感中文名

        设计：
        - 不破坏现有 ``get_latest_emotion()`` 方法签名；
        - 复用 ``self.get_latest_emotion()`` 拉取数据；
        - 在 emotion_history 表未存 Plutchik 原始 8 维数据时，
          基于 overall_score + emotional_tone 派生合理默认；
        - 失败 / 无记录时返回 ``{}``（路由层保持 200 + 空 dict）。
        """
        try:
            latest = self.get_latest_emotion()
        except Exception:  # noqa: BLE001
            return {}

        if not latest:
            return {}

        try:
            overall_score = int(latest.get('overall_score') or 0)
        except (TypeError, ValueError):
            overall_score = 0
        emotional_tone = latest.get('emotional_tone', '中性') or '中性'
        timestamp = latest.get('timestamp') or latest.get('created_at') or ''

        plutchik = self._derive_plutchik_from_legacy(overall_score, emotional_tone)
        # additive_scores：把 0-1 强度乘回 0-100，与前端雷达图 max=10/100 兼容
        additive = {k: round(float(v) * 100.0, 2) for k, v in plutchik.items()}

        try:
            dominant_key = max(plutchik.items(), key=lambda kv: kv[1])[0]
        except Exception:  # noqa: BLE001
            dominant_key = 'joy'
        dominant = self.PLUTCHIK_CN.get(dominant_key, dominant_key)
        # 整体强度过低 → 标记为"平静"
        if max(plutchik.values()) < 0.15:
            dominant = '平静'

        return {
            'timestamp': timestamp,
            'additive_scores': additive,
            'plutchik': {k: round(float(v), 3) for k, v in plutchik.items()},
            'dominant': dominant,
        }

    def generate_tone_prompt(self) -> str:
        """
        根据最新情感分析生成对话语气提示

        Returns:
            语气提示文本，如果没有情感数据则返回空字符串
        """
        latest_emotion = self.get_latest_emotion()
        if not latest_emotion:
            debug_logger.log_info('EmotionAnalyzer', '无情感数据，无法生成语气提示')
            return ""

        debug_logger.log_info('EmotionAnalyzer', '开始生成情感语气提示', {
            'has_emotion_data': True
        })

        # 提取关键信息
        relationship_type = latest_emotion.get('relationship_type', '普通朋友')
        emotional_tone = latest_emotion.get('emotional_tone', '中性')
        overall_score = latest_emotion.get('overall_score', 50)
        sentiment = latest_emotion.get('sentiment', 'neutral')
        impression = latest_emotion.get('impression', '')

        debug_logger.log_info('EmotionAnalyzer', '提取情感数据', {
            'relationship_type': relationship_type,
            'emotional_tone': emotional_tone,
            'overall_score': overall_score,
            'sentiment': sentiment
        })

        # 构建语气提示
        prompt_parts = ["\n【当前情感关系状态】"]
        prompt_parts.append(f"你和用户的关系类型：{relationship_type}")
        prompt_parts.append(f"整体情感基调：{emotional_tone}")
        prompt_parts.append(f"关系总评分：{overall_score}/100")
        
        # 添加印象摘要
        if impression:
            # 取印象的前100字作为摘要
            impression_summary = impression[:100] + "..." if len(impression) > 100 else impression
            prompt_parts.append(f"\n【对用户的印象】\n{impression_summary}")

        # 添加对话建议
        prompt_parts.append("\n【对话语气建议】")
        
        # 根据评分给出建议
        if overall_score >= 81:
            prompt_parts.append("• 关系非常好，用户对你印象很正面")
            prompt_parts.append("• 可以更自在地表达，像好友一样交流")
            prompt_parts.append("• 继续保持热情积极的态度")
        elif overall_score >= 61:
            prompt_parts.append("• 关系较好，用户对你印象偏正面")
            prompt_parts.append("• 可以适当分享更多个人想法")
            prompt_parts.append("• 保持友好但不过分亲密")
        elif overall_score >= 41:
            prompt_parts.append("• 关系一般，印象中性")
            prompt_parts.append("• 保持礼貌友好的态度")
            prompt_parts.append("• 需要更用心经营关系")
        elif overall_score >= 21:
            prompt_parts.append("• 印象偏负面，需要改善")
            prompt_parts.append("• 更加关注用户需求和感受")
            prompt_parts.append("• 避免可能引起反感的行为")
        else:
            prompt_parts.append("• 印象很负面，关系需要修复")
            prompt_parts.append("• 更谨慎地选择用词和态度")
            prompt_parts.append("• 努力重建信任")

        # 根据情感基调调整语气
        if emotional_tone == "积极":
            prompt_parts.append("• 保持积极乐观的态度，继续营造愉快氛围")
        elif emotional_tone == "消极":
            prompt_parts.append("• 注意用户情绪，给予更多关心和支持")
        else:
            prompt_parts.append("• 保持友好平和的态度")

        # 根据关系类型调整语气
        if relationship_type in ["知己", "亲密朋友", "好友"]:
            prompt_parts.append("• 可以使用更亲昵的语气，像老朋友一样交流")
        elif relationship_type in ["朋友", "熟人"]:
            prompt_parts.append("• 保持友好但不过分亲密的语气")
        elif relationship_type in ["初识", "陌生人"]:
            prompt_parts.append("• 保持礼貌友好，逐步建立信任")

        prompt_parts.append("\n⚠️ 请根据以上印象和状态调整你的回复语气和态度，使对话更自然、更贴合当前关系。")

        tone_prompt = '\n'.join(prompt_parts)

        debug_logger.log_info('EmotionAnalyzer', '情感语气提示生成完成', {
            'prompt_length': len(tone_prompt),
            'relationship_type': relationship_type,
            'overall_score': overall_score
        })

        return tone_prompt

    def export_emotion_data(self, filepath: str):
        """
        导出情感数据到文件

        Args:
            filepath: 导出文件路径
        """
        debug_logger.log_info('EmotionAnalyzer', '开始导出情感数据', {
            'filepath': filepath,
            'data_count': len(self.emotion_history)
        })

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.emotion_history, f, ensure_ascii=False, indent=2)

            debug_logger.log_info('EmotionAnalyzer', '情感数据导出成功', {
                'filepath': filepath
            })
            print(f"情感数据已导出到: {filepath}")
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'导出情感数据时出错: {str(e)}', e)
            print(f"导出情感数据时出错: {e}")

    def import_emotion_data(self, filepath: str):
        """
        从文件导入情感数据

        Args:
            filepath: 导入文件路径
        """
        debug_logger.log_info('EmotionAnalyzer', '开始导入情感数据', {
            'filepath': filepath
        })

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.emotion_history = json.load(f)

                debug_logger.log_info('EmotionAnalyzer', '情感数据导入成功', {
                    'filepath': filepath,
                    'data_count': len(self.emotion_history)
                })
                print(f"情感数据已从文件加载: {len(self.emotion_history)} 条记录")
            else:
                debug_logger.log_info('EmotionAnalyzer', '导入文件不存在', {
                    'filepath': filepath
                })
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'导入情感数据时出错: {str(e)}', e)
            print(f"导入情感数据时出错: {e}")


def format_emotion_summary(emotion_data: Dict[str, Any]) -> str:
    """
    格式化情感分析结果为可读文本

    Args:
        emotion_data: 情感数据

    Returns:
        格式化后的文本
    """
    impression = emotion_data.get('impression', '暂无印象')
    is_initial = emotion_data.get('is_initial', False)
    
    # 评分信息
    if is_initial:
        score_text = f"初始评分: {emotion_data.get('overall_score', 0)}/35"
    else:
        score_change = emotion_data.get('score_change', 0)
        previous_score = emotion_data.get('previous_score', 0)
        current_score = emotion_data.get('overall_score', 0)
        score_text = f"累计评分: {current_score}/100 (上次: {previous_score}, 变化: {score_change:+d})"
    
    summary = f"""
【情感关系分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
关系类型: {emotion_data.get('relationship_type', '未知')}
情感基调: {emotion_data.get('emotional_tone', '未知')}
{score_text}
印象倾向: {emotion_data.get('sentiment', 'neutral')}

【对用户的印象】
{impression}

【关系总结】
{emotion_data.get('analysis', '暂无分析')}

【主要话题】
{', '.join(emotion_data.get('key_topics', [])) if emotion_data.get('key_topics') else '暂无'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    return summary.strip()


# ==================== P2: PlutchikEmotionWheel ====================

class PlutchikEmotionWheel:
    """
    Plutchik 情绪轮（8 基本情绪）。
    与累加评分（EmotionRelationshipAnalyzer）并行：累加 = 关系状态，Plutchik = 当下情绪。
    情绪随时间衰减；支持复合表达（"开心但有点紧张"）。
    """

    EMOTIONS = [
        'joy', 'trust', 'fear', 'surprise',
        'sadness', 'disgust', 'anger', 'anticipation',
    ]
    EMOTION_CN = {
        'joy': '喜悦', 'trust': '信任', 'fear': '恐惧', 'surprise': '惊讶',
        'sadness': '悲伤', 'disgust': '厌恶', 'anger': '愤怒', 'anticipation': '期待',
    }
    OPPOSITES = {
        'joy': 'sadness', 'sadness': 'joy',
        'trust': 'disgust', 'disgust': 'trust',
        'fear': 'anger', 'anger': 'fear',
        'surprise': 'anticipation', 'anticipation': 'surprise',
    }
    DEFAULT_HALF_LIFE_HOURS = 24.0

    def __init__(self, db_manager: DatabaseManager = None,
                 half_life_hours: float = DEFAULT_HALF_LIFE_HOURS):
        """
        Args:
            db_manager: 数据库管理器
            half_life_hours: 情绪半衰期（小时）
        """
        self.db = db_manager
        self.half_life_hours = float(half_life_hours)
        self.enabled = ENABLE_EMOTION_WHEEL

    def decay_emotions(self, state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        按指数衰减应用至 state['emotions']。
        state['emotions'] 为 {emotion_key: intensity(0-1)}
        state['last_update'] 为 ISO 时间字符串。
        """
        if not state or 'emotions' not in state:
            return self._default_state(now)
        now = now or datetime.now()
        last = self._parse_iso(state.get('last_update')) or now
        elapsed_h = max(0.0, (now - last).total_seconds() / 3600.0)
        if elapsed_h <= 0:
            return state
        factor = math.pow(0.5, elapsed_h / self.half_life_hours)
        new_emotions = {}
        for k, v in (state.get('emotions') or {}).items():
            try:
                new_emotions[k] = max(0.0, min(1.0, float(v) * factor))
            except (TypeError, ValueError):
                continue
        state['emotions'] = new_emotions
        state['last_update'] = now.isoformat()
        return state

    def nudge_emotion(self, emotions: Dict[str, float],
                      key: str, delta: float) -> Dict[str, float]:
        """
        对单个情绪做 +/- 调整，clamp 至 [0, 1]。
        """
        if key not in self.EMOTIONS:
            return emotions
        out = dict(emotions or {})
        out[key] = max(0.0, min(1.0, float(out.get(key, 0.0)) + float(delta)))
        return out

    def profile_from_basic(self, emotions: Dict[str, float],
                           now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        从 8 基本情绪推导 profile：
        - primary: 主导情绪
        - secondary: 第二情绪
        - intensity: 平均强度
        - compound_desc: 复合表达（"开心但有点紧张"）
        - tone_label: 1-3 词标签
        """
        if not emotions:
            return {
                'primary': '平静', 'secondary': None, 'intensity': 0.0,
                'compound_desc': '平静', 'tone_label': '平静',
            }
        sorted_items = sorted(
            emotions.items(), key=lambda kv: kv[1], reverse=True
        )
        primary_k, primary_v = sorted_items[0]
        primary_cn = self.EMOTION_CN.get(primary_k, primary_k)

        secondary_cn = None
        if len(sorted_items) > 1 and sorted_items[1][1] >= 0.3:
            secondary_cn = self.EMOTION_CN.get(sorted_items[1][0], sorted_items[1][0])

        avg = sum(emotions.values()) / max(1, len(emotions))
        compound = primary_cn
        if secondary_cn and primary_v > 0.3 and sorted_items[1][1] >= 0.3:
            compound = f"{primary_cn}但有点{secondary_cn}"

        if avg < 0.15:
            tone = '平静'
        elif avg < 0.4:
            tone = primary_cn
        elif avg < 0.7:
            tone = f"明显{primary_cn}"
        else:
            tone = f"强烈{primary_cn}"

        return {
            'primary': primary_cn, 'secondary': secondary_cn,
            'intensity': round(avg, 3), 'compound_desc': compound,
            'tone_label': tone,
        }

    def format_emotion_hint(self, state: Dict[str, Any]) -> str:
        """
        渲染为 prompt 文本（与 generate_tone_prompt 平行注入）。
        """
        if not self.enabled:
            return ""
        if not state or not state.get('emotions'):
            return ""
        profile = self.profile_from_basic(state.get('emotions', {}))
        lines = ["【当下情绪】"]
        lines.append(f"主导：{profile['primary']}（强度 {profile['intensity']:.2f}）")
        if profile.get('secondary'):
            lines.append(f"次要：{profile['secondary']}")
        lines.append(f"综合：{profile['compound_desc']}")
        lines.append(f"语气：{profile['tone_label']}")
        return "\n".join(lines)

    def _default_state(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now()
        return {
            'emotions': {k: 0.0 for k in self.EMOTIONS},
            'last_update': now.isoformat(),
        }

    @staticmethod
    def _parse_iso(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

