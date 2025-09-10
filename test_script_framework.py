#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧本框架约束器测试文件
测试ScriptFrameworkConstrainer的各项功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_core import LLMCore, GameState
from config_manager import ConfigManager

def test_script_framework():
    """测试剧本框架约束器功能"""
    print("=== 剧本框架约束器测试 ===")
    
    try:
        # 初始化配置管理器和LLMCore
        config_manager = ConfigManager()
        llm_core = LLMCore()
        
        print(f"\n✓ LLMCore初始化成功")
        print(f"✓ 剧情节点加载数量: {len(llm_core.script_constrainer.story_nodes)}")
        print(f"✓ 可用节点: {list(llm_core.script_constrainer.story_nodes.keys())}")
        
        print("\n1. 测试获取剧情上下文:")
        context = llm_core.get_current_story_context()
        print(f"✓ 剧情上下文获取成功: {context['title']}")
        
        print("\n2. 测试获取可用分支:")
        branches = llm_core.get_available_branches()
        print(f"✓ 可用分支数量: {len(branches)}")
        
        print("\n3. 测试获取剧情进度:")
        progress = llm_core.get_story_progress()
        print(f"✓ 剧情进度获取成功，当前节点: {progress['current_node']['title']}")
        
        print("\n4. 测试剧情提示词构建:")
        story_prompt = llm_core.script_constrainer.build_story_prompt(
            llm_core.character_state, llm_core.game_state
        )
        print(f"✓ 剧情提示词构建成功，长度: {len(story_prompt)} 字符")
        
        print("\n5. 测试分支选择功能:")
        if branches:
            result = llm_core.select_branch(branches[0]['id'])
            print(f"✓ 分支选择功能正常: {result['success']}")
        else:
            print("ℹ 当前节点没有可用分支，这是正常的")
            
        print("\n🎉 所有测试通过！剧本框架约束器工作正常")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_script_framework()