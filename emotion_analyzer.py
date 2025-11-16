"""
情感关系分析模块
基于近10轮对话，使用LLM分析与对话人的情感关系
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
    分析用户和AI角色之间的情感关系变化
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

        # 情感关系维度
        self.emotion_dimensions = [
            "亲密度",      # 关系亲密程度
            "信任度",      # 相互信任程度
            "愉悦度",      # 对话中的愉悦感
            "共鸣度",      # 情感共鸣程度
            "依赖度"       # 对对方的依赖程度
        ]

        # 检查是否需要从JSON迁移数据
        if os.path.exists('emotion_data.json'):
            print("○ 检测到旧的情感数据JSON文件，正在迁移...")
            self._migrate_from_json('emotion_data.json')
            os.rename('emotion_data.json', 'emotion_data.json.bak')
            print("✓ 情感数据已迁移，JSON文件已备份")

        print("✓ 情感关系分析器已初始化（使用数据库存储）")

    def analyze_emotion_relationship(self,
                                    messages: List[Dict[str, str]],
                                    character_name: str = "AI") -> Dict[str, Any]:
        """
        分析情感关系

        Args:
            messages: 对话消息列表（最近10轮，即20条消息）
            character_name: AI角色名称

        Returns:
            情感分析结果，包含各维度评分和描述
        """
        debug_logger.log_module('EmotionAnalyzer', '开始情感关系分析', {
            'total_messages': len(messages),
            'character_name': character_name
        })

        # 只取最近10轮（20条消息）
        recent_messages = messages[-20:] if len(messages) > 20 else messages

        if len(recent_messages) < 2:
            # 对话太少，返回默认值
            debug_logger.log_info('EmotionAnalyzer', '对话数量不足，返回默认情感数据', {
                'message_count': len(recent_messages)
            })
            return self._get_default_emotion_result()

        # 构建分析提示词
        conversation_text = self._format_conversation(recent_messages)
        prompt = self._build_analysis_prompt(conversation_text, character_name)

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
            emotion_data = self._parse_emotion_result(result)

            # 添加时间戳
            emotion_data['timestamp'] = datetime.now().isoformat()
            emotion_data['message_count'] = len(recent_messages)

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

    def _build_analysis_prompt(self, conversation_text: str, character_name: str) -> str:
        """
        构建情感分析提示词

        Args:
            conversation_text: 对话文本
            character_name: AI角色名称

        Returns:
            分析提示词
        """
        prompt = f"""你是一位专业的心理分析师，擅长分析对话中的情感关系。

请仔细分析以下对话内容，评估用户和AI角色"{character_name}"之间的情感关系。

对话内容：
{conversation_text}

请从以下5个维度进行评估（每个维度0-100分）：
1. 亲密度：双方关系的亲密程度，陌生(0-20)、普通(21-40)、熟悉(41-60)、亲密(61-80)、非常亲密(81-100)
2. 信任度：用户对AI的信任程度，表现为是否愿意分享个人信息、情感等
3. 愉悦度：对话过程中用户的愉悦和满意程度
4. 共鸣度：双方在话题和情感上的共鸣程度
5. 依赖度：用户对AI的依赖程度，表现为求助、咨询等行为

请以JSON格式返回分析结果，格式如下：
{{
    "亲密度": 分数,
    "信任度": 分数,
    "愉悦度": 分数,
    "共鸣度": 分数,
    "依赖度": 分数,
    "overall_score": 总体评分(0-100),
    "relationship_type": "关系类型(如：陌生人、朋友、知己等)",
    "emotional_tone": "整体情感基调(如：积极、中性、消极)",
    "key_topics": ["主要话题1", "主要话题2", "主要话题3"],
    "analysis": "简短的关系分析描述(100字以内)"
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

    def _parse_emotion_result(self, result_text: str) -> Dict[str, Any]:
        """
        解析LLM返回的情感分析结果

        Args:
            result_text: LLM返回的文本

        Returns:
            解析后的情感数据
        """
        debug_logger.log_info('EmotionAnalyzer', '开始解析LLM返回结果', {
            'result_length': len(result_text)
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
            required_fields = {
                "亲密度": 50,
                "信任度": 50,
                "愉悦度": 50,
                "共鸣度": 50,
                "依赖度": 50,
                "overall_score": 50,
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
            "亲密度": 30,
            "信任度": 30,
            "愉悦度": 50,
            "共鸣度": 30,
            "依赖度": 20,
            "overall_score": 32,
            "relationship_type": "初识",
            "emotional_tone": "中性",
            "key_topics": [],
            "analysis": "对话轮数较少，关系尚在建立初期。",
            "timestamp": datetime.now().isoformat(),
            "message_count": 0
        }

    def get_emotion_trend(self) -> List[Dict[str, Any]]:
        """
        获取情感关系变化趋势（从数据库）

        Returns:
            历史情感数据列表
        """
        emotion_history = self.db.get_emotion_history()

        # 转换为旧格式以保持兼容性
        result = []
        for emotion in emotion_history:
            result.append({
                "亲密度": emotion.get('intimacy', 0),
                "信任度": emotion.get('trust', 0),
                "愉悦度": emotion.get('pleasure', 0),
                "共鸣度": emotion.get('resonance', 0),
                "依赖度": emotion.get('dependence', 0),
                "overall_score": emotion.get('overall_score', 0),
                "relationship_type": emotion.get('relationship_type', '未知'),
                "emotional_tone": emotion.get('emotional_tone', '未知'),
                "analysis": emotion.get('analysis_summary', ''),
                "timestamp": emotion.get('created_at', ''),
                "uuid": emotion.get('uuid', '')
            })

        return result

    def get_latest_emotion(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的情感分析结果（从数据库）

        Returns:
            最新情感数据，如果没有则返回None
        """
        latest = self.db.get_latest_emotion()

        if not latest:
            return None

        # 转换为旧格式以保持兼容性
        return {
            "亲密度": latest.get('intimacy', 0),
            "信任度": latest.get('trust', 0),
            "愉悦度": latest.get('pleasure', 0),
            "共鸣度": latest.get('resonance', 0),
            "依赖度": latest.get('dependence', 0),
            "overall_score": latest.get('overall_score', 0),
            "relationship_type": latest.get('relationship_type', '未知'),
            "emotional_tone": latest.get('emotional_tone', '未知'),
            "analysis": latest.get('analysis_summary', ''),
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
        intimacy = latest_emotion.get('亲密度', 50)
        trust = latest_emotion.get('信任度', 50)
        pleasure = latest_emotion.get('愉悦度', 50)
        resonance = latest_emotion.get('共鸣度', 50)
        dependence = latest_emotion.get('依赖度', 50)
        overall_score = latest_emotion.get('overall_score', 50)

        debug_logger.log_info('EmotionAnalyzer', '提取情感维度数据', {
            'relationship_type': relationship_type,
            'emotional_tone': emotional_tone,
            'intimacy': intimacy,
            'trust': trust,
            'pleasure': pleasure,
            'resonance': resonance,
            'dependence': dependence,
            'overall_score': overall_score
        })

        # 构建语气提示
        prompt_parts = ["\n【当前情感关系状态】"]
        prompt_parts.append(f"你和用户的关系类型：{relationship_type}")
        prompt_parts.append(f"整体情感基调：{emotional_tone}")
        prompt_parts.append(f"关系总评分：{overall_score}/100")

        prompt_parts.append("\n【各维度情感状态】")

        # 亲密度
        intimacy_desc = ""
        if intimacy >= 80:
            intimacy_desc = "非常亲密，可以像密友一样交流"
        elif intimacy >= 60:
            intimacy_desc = "比较亲密，可以分享更多个人想法"
        elif intimacy >= 40:
            intimacy_desc = "普通熟悉，保持适当距离感"
        else:
            intimacy_desc = "还不够熟悉，需要更温和友好"
        prompt_parts.append(f"• 亲密度: {intimacy}/100 - {intimacy_desc}")

        # 信任度
        trust_desc = ""
        if trust >= 80:
            trust_desc = "用户非常信任你，可以给出更深入的建议"
        elif trust >= 60:
            trust_desc = "用户较为信任，可以分享更多见解"
        elif trust >= 40:
            trust_desc = "信任度一般，需要更真诚的态度"
        else:
            trust_desc = "信任度较低，需要展现更多可靠性"
        prompt_parts.append(f"• 信任度: {trust}/100 - {trust_desc}")

        # 愉悦度
        pleasure_desc = ""
        if pleasure >= 80:
            pleasure_desc = "对话氛围很好，保持活泼积极"
        elif pleasure >= 60:
            pleasure_desc = "对话较愉快，继续保持"
        elif pleasure >= 40:
            pleasure_desc = "对话较平淡，可以更有趣些"
        else:
            pleasure_desc = "用户可能不太开心，需要更关心体贴"
        prompt_parts.append(f"• 愉悦度: {pleasure}/100 - {pleasure_desc}")

        # 共鸣度
        resonance_desc = ""
        if resonance >= 80:
            resonance_desc = "很有共鸣，可以深入探讨共同话题"
        elif resonance >= 60:
            resonance_desc = "有一定共鸣，继续寻找共同点"
        elif resonance >= 40:
            resonance_desc = "共鸣一般，需要更理解用户"
        else:
            resonance_desc = "缺乏共鸣，需要更多倾听和理解"
        prompt_parts.append(f"• 共鸣度: {resonance}/100 - {resonance_desc}")

        # 依赖度
        dependence_desc = ""
        if dependence >= 80:
            dependence_desc = "用户很依赖你，要负责任地给予支持"
        elif dependence >= 60:
            dependence_desc = "用户较依赖你，继续提供帮助"
        elif dependence >= 40:
            dependence_desc = "依赖度一般，可以提供更多价值"
        else:
            dependence_desc = "依赖度较低，需要展现更多能力"
        prompt_parts.append(f"• 依赖度: {dependence}/100 - {dependence_desc}")

        # 添加对话建议
        prompt_parts.append("\n【对话语气建议】")

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
            prompt_parts.append("• 可以分享更多个人想法和情感")
        elif relationship_type in ["朋友", "熟人"]:
            prompt_parts.append("• 保持友好但不过分亲密的语气")
            prompt_parts.append("• 适度分享，注意边界")
        elif relationship_type in ["初识", "陌生人"]:
            prompt_parts.append("• 保持礼貌友好，但不要太过热情")
            prompt_parts.append("• 逐步建立信任，不要急于深入")

        # 根据综合评分调整
        if overall_score >= 80:
            prompt_parts.append("• 关系很好，可以更自在地表达")
        elif overall_score >= 60:
            prompt_parts.append("• 关系不错，继续保持和发展")
        elif overall_score >= 40:
            prompt_parts.append("• 关系一般，需要更用心经营")
        else:
            prompt_parts.append("• 关系需要改善，要更关注用户需求")

        prompt_parts.append("\n⚠️ 请根据以上情感状态调整你的回复语气和态度，使对话更自然、更贴合当前关系。")

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
    summary = f"""
【情感关系分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
关系类型: {emotion_data.get('relationship_type', '未知')}
情感基调: {emotion_data.get('emotional_tone', '未知')}
总体评分: {emotion_data.get('overall_score', 0)}/100

【各维度评分】
  亲密度: {emotion_data.get('亲密度', 0)}/100
  信任度: {emotion_data.get('信任度', 0)}/100
  愉悦度: {emotion_data.get('愉悦度', 0)}/100
  共鸣度: {emotion_data.get('共鸣度', 0)}/100
  依赖度: {emotion_data.get('依赖度', 0)}/100

【关系分析】
{emotion_data.get('analysis', '暂无分析')}

【主要话题】
{', '.join(emotion_data.get('key_topics', [])) if emotion_data.get('key_topics') else '暂无'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    return summary.strip()

