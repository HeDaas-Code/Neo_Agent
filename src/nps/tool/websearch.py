"""
WebSearch - 网络搜索工具
使用 SerpAPI 进行网络搜索，获取实时信息
"""

import os
import requests
from typing import Dict, Any, List, Optional
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


def search_web(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    使用SerpAPI进行网络搜索
    
    Args:
        context: 执行上下文，应包含'query'键表示搜索查询
        
    Returns:
        包含搜索结果的字典
    """
    if not context or 'query' not in context:
        return {
            'error': '缺少搜索查询参数',
            'success': False
        }
    
    query = context['query']
    api_key = os.getenv('SERPAPI_API_KEY', '')
    
    if not api_key:
        debug_logger.log_warning('WebSearch', 'SERPAPI_API_KEY未配置')
        return {
            'error': 'SerpAPI密钥未配置，请在.env文件中设置SERPAPI_API_KEY',
            'success': False
        }
    
    try:
        # 构建SerpAPI请求
        params = {
            'q': query,
            'api_key': api_key,
            'engine': context.get('engine', 'google'),  # 默认使用Google搜索
            'num': context.get('num_results', 5),  # 默认返回5个结果
            'hl': context.get('language', 'zh-cn'),  # 默认中文
        }
        
        debug_logger.log_module('WebSearch', f'搜索查询: {query}')
        
        # 发送请求
        response = requests.get(
            'https://serpapi.com/search',
            params=params,
            timeout=context.get('timeout', 10)
        )
        
        response.raise_for_status()
        data = response.json()
        
        # 解析搜索结果
        organic_results = data.get('organic_results', [])
        answer_box = data.get('answer_box', {})
        knowledge_graph = data.get('knowledge_graph', {})
        
        # 构建结构化结果
        results = []
        for item in organic_results[:context.get('num_results', 5)]:
            results.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'position': item.get('position', 0)
            })
        
        # 整理返回数据
        search_result = {
            'success': True,
            'query': query,
            'num_results': len(results),
            'results': results
        }
        
        # 添加答案框（如果有）
        if answer_box:
            search_result['answer_box'] = {
                'title': answer_box.get('title', ''),
                'snippet': answer_box.get('snippet', ''),
                'answer': answer_box.get('answer', '')
            }
        
        # 添加知识图谱（如果有）
        if knowledge_graph:
            search_result['knowledge_graph'] = {
                'title': knowledge_graph.get('title', ''),
                'type': knowledge_graph.get('type', ''),
                'description': knowledge_graph.get('description', '')
            }
        
        # 生成简洁的上下文描述
        context_desc = f"搜索「{query}」找到{len(results)}个结果"
        if answer_box:
            context_desc += f"，答案框显示：{answer_box.get('answer', answer_box.get('snippet', ''))[:100]}"
        search_result['context'] = context_desc
        
        debug_logger.log_info('WebSearch', f'搜索完成，找到{len(results)}个结果')
        return search_result
        
    except requests.exceptions.Timeout:
        debug_logger.log_error('WebSearch', '搜索请求超时', None)
        return {
            'error': '搜索请求超时',
            'success': False
        }
    except requests.exceptions.RequestException as e:
        debug_logger.log_error('WebSearch', '搜索请求失败', e)
        return {
            'error': f'搜索请求失败: {str(e)}',
            'success': False
        }
    except Exception as e:
        debug_logger.log_error('WebSearch', '搜索过程出错', e)
        return {
            'error': f'搜索失败: {str(e)}',
            'success': False
        }


def format_search_results_for_agent(results: Dict[str, Any]) -> str:
    """
    将搜索结果格式化为智能体可读的文本
    
    Args:
        results: search_web返回的结果字典
        
    Returns:
        格式化的文本描述
    """
    if not results.get('success'):
        return f"搜索失败：{results.get('error', '未知错误')}"
    
    output = [f"搜索「{results['query']}」的结果：\n"]
    
    # 答案框
    if 'answer_box' in results:
        answer_box = results['answer_box']
        output.append(f"【直接答案】{answer_box.get('answer', answer_box.get('snippet', ''))}\n")
    
    # 知识图谱
    if 'knowledge_graph' in results:
        kg = results['knowledge_graph']
        output.append(f"【知识卡片】{kg.get('title', '')}")
        if kg.get('description'):
            output.append(f"{kg['description']}\n")
    
    # 搜索结果
    if results.get('results'):
        output.append(f"\n【搜索结果】共{len(results['results'])}条：")
        for i, item in enumerate(results['results'], 1):
            output.append(f"\n{i}. {item['title']}")
            output.append(f"   {item['snippet']}")
            output.append(f"   来源：{item['link']}")
    
    return '\n'.join(output)
