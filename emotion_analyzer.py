"""
情感关系分析模块
基于近15轮对话，使用LLM生成对用户的印象并评分
使用数据库替代JSON文件存储
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class EmotionRelationshipAnalyzer:
    """
    情感关系分析器
    基于角色设定和最近15轮对话，生成对用户的印象并评分
    不再使用多维度分析，而是生成综合印象和正负面评分
    使用数据库存储替代JSON文件
    """

    def __init__(self,
                 db_manager: DatabaseManager = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化情感关系分析器

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()

        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'deepseek-ai/DeepSeek-V3')

        # 检查是否需要从JSON迁移数据
        if os.path.exists('emotion_data.json'):
            print("○ 检测到旧的情感数据JSON文件，正在迁移...")
            self._migrate_from_json('emotion_data.json')
            os.rename('emotion_data.json', 'emotion_data.json.bak')
            print("✓ 情感数据已迁移，JSON文件已备份")

        print("✓ 情感关系分析器已初始化（使用数据库存储）")

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
        
        # 自动判断是初次评估还是更新评估
        if is_initial is None:
            is_initial = (current_score == 0 or latest_emotion is None)
        
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
                # 初次评估：使用返回的分数作为初始分数
                final_score = emotion_data.get('overall_score', 0)
                debug_logger.log_info('EmotionAnalyzer', '初次评估', {
                    'initial_score': final_score
                })
            else:
                # 更新评估：当前分数 + 变化量
                score_change = emotion_data.get('score_change', 0)
                final_score = current_score + score_change
                # 确保分数在合理范围内（0-100）
                final_score = max(0, min(100, final_score))
                emotion_data['overall_score'] = final_score
                emotion_data['previous_score'] = current_score
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
            # 将印象和分析合并到analysis_summary中
            impression = emotion_data.get('impression', '')
            analysis = emotion_data.get('analysis', '')
            is_initial = emotion_data.get('is_initial', False)
            
            # 添加评分信息到摘要
            if is_initial:
                score_info = f"【初始评分】{emotion_data.get('overall_score', 0)}/35\n\n"
            else:
                score_change = emotion_data.get('score_change', 0)
                previous_score = emotion_data.get('previous_score', 0)
                current_score = emotion_data.get('overall_score', 0)
                score_info = f"【评分变化】{previous_score} → {current_score} ({score_change:+d})\n\n"
            
            combined_summary = f"{score_info}【印象】\n{impression}\n\n【总结】\n{analysis}"
            
            self.db.add_emotion_analysis(
                relationship_type=emotion_data.get('relationship_type', '未知'),
                emotional_tone=emotion_data.get('emotional_tone', '未知'),
                overall_score=emotion_data.get('overall_score', 0),
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
        构建情感分析提示词

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
        调用LLM API

        Args:
            prompt: 提示词

        Returns:
            LLM返回的文本
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': self.model_name,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,  # 使用较低温度以获得更稳定的结果
            'max_tokens': 1000
        }

        debug_logger.log_request('EmotionAnalyzer', self.api_url, data, headers)

        import time
        start_time = time.time()

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                debug_logger.log_response('EmotionAnalyzer', result, response.status_code, elapsed_time)

                content = result['choices'][0]['message']['content']
                debug_logger.log_info('EmotionAnalyzer', 'API调用成功', {
                    'response_length': len(content),
                    'elapsed_time': elapsed_time
                })
                return content
            else:
                debug_logger.log_error('EmotionAnalyzer',
                    f'API调用失败: {response.status_code}',
                    Exception(response.text))
                raise Exception(f"API调用失败: {response.status_code}, {response.text}")

        except requests.exceptions.Timeout as e:
            debug_logger.log_error('EmotionAnalyzer', 'API请求超时', e)
            raise Exception(f"API请求超时: {str(e)}")
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'API调用异常: {str(e)}', e)
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
            return self._get_default_emotion_result()
        except Exception as e:
            debug_logger.log_error('EmotionAnalyzer', f'解析情感结果时出错: {str(e)}', e)
            print(f"解析情感结果时出错: {e}")
            print(f"原始结果: {result_text}")
            return self._get_default_emotion_result()

    def _get_default_emotion_result(self) -> Dict[str, Any]:
        """
        获取默认情感分析结果

        Returns:
            默认情感数据
        """
        return {
            "impression": "对话轮数较少，尚未形成明确印象。用户表现正常，期待更多交流。",
            "overall_score": 15,  # 默认初始分数中间值
            "sentiment": "neutral",
            "relationship_type": "初识",
            "emotional_tone": "中性",
            "key_topics": [],
            "analysis": "对话刚开始，关系尚在建立初期。",
            "timestamp": datetime.now().isoformat(),
            "message_count": 0,
            "is_initial": True
        }

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
                parts = analysis_summary.split("【总结】")
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
            score: 0-100的评分
            
        Returns:
            情感倾向：positive/neutral/negative
        """
        if score >= 61:
            return "positive"
        elif score >= 41:
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
            parts = analysis_summary.split("【总结】")
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

