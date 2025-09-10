#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test all game actions
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_core import LLMCore

async def test_all_game_actions():
    """Test all game actions"""
    # Create LLMCore instance
    llm_core = LLMCore()
    
    # Define all test cases
    test_cases = [
        # Look actions
        {
            'name': 'Look Actions - General',
            'inputs': ['看看周围', '观察环境', '查看当前位置', '这里是哪里']
        },
        {
            'name': 'Look Actions - Specific Locations',
            'inputs': ['看看舰桥', '查看工程舱', '观察生活区']
        },
        
        # Move actions
        {
            'name': 'Move Actions',
            'inputs': ['去舰桥', '移动到工程舱', '前往生活区', '走向货舱']
        },
        
        # Take actions
        {
            'name': 'Take Actions',
            'inputs': ['拿起导航手册', '拾取工具', '捡起医疗包', '取走通讯记录']
        },
        
        # Use actions
        {
            'name': 'Use Actions',
            'inputs': ['使用医疗包', '打开导航手册', '查看通讯记录', '使用维修工具']
        },
        
        # Talk actions
        {
            'name': 'Talk Actions',
            'inputs': ['你好，我是AI系统', '告诉我你的状况', '我们需要合作', '你感觉怎么样']
        },
        
        # Complex actions
        {
            'name': 'Complex Actions',
            'inputs': [
                '先看看周围，然后去舰桥',
                '拿起工具后使用它',
                '检查这里的物品并告诉我你的想法'
            ]
        },
        
        # Natural language variants
        {
            'name': 'Natural Language Variants',
            'inputs': [
                '我想了解一下当前的情况',
                '能帮我分析一下我们的处境吗',
                '系统，报告飞船状态',
                '艾莉克斯，你现在在哪里'
            ]
        }
    ]
    
    print("=== Starting All Game Actions Test ===")
    print(f"Total test categories: {len(test_cases)}")
    
    for i, test_category in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Category {i}/{len(test_cases)}: {test_category['name']}")
        print(f"{'='*60}")
        
        for j, test_input in enumerate(test_category['inputs'], 1):
            print(f"\n--- Test {i}.{j}: '{test_input}' ---")
            
            try:
                # Call dialogue processing method
                response = await llm_core.process_dialogue(test_input)
                print(f"\n🤖 AI Response:")
                print(response)
                print(f"\n✅ Test {i}.{j} completed")
                
                # Add short delay to avoid API calls too fast
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Test {i}.{j} failed: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"\n{'='*60}")
    print("=== All Action Tests Completed ===")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_all_game_actions())