#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM驱动AVG游戏核心系统

这个测试文件验证了LLM核心系统的主要功能：
- 模型管理和API调用
- 记忆系统和向量存储
- 角色控制和对话生成
- 知识图谱管理
- 游戏状态更新
"""

import asyncio
import json
import os
from llm_core import LLMCore
from config_manager import config_manager


def test_basic_initialization():
    """测试基本初始化功能"""
    print("=== 测试基本初始化 ===")
    
    try:
        # 初始化核心系统
        core = LLMCore("config.json")
        print("✓ LLM核心系统初始化成功")
        
        # 检查配置加载
        print(f"✓ 角色名称: {core.character_controller.character_name}")
        print(f"✓ 当前权限等级: {core.game_state.permission_level}")
        print(f"✓ 角色健康状态: {core.game_state.character_health}")
        
        return True
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return False


def test_memory_system():
    """测试记忆系统功能"""
    print("\n=== 测试记忆系统 ===")
    
    try:
        core = LLMCore("config.json")
        
        # 测试记忆存储
        test_memory = "玩家询问了飞船的基本布局信息"
        memory_id = core.memory_system.store_memory(test_memory, {
            'type': 'dialogue',
            'timestamp': 1234567890,
            'character_name': '艾莉克斯',
            'test_mode': True
        })
        print(f"✓ 记忆存储成功，ID: {memory_id}")
        
        # 测试记忆检索
        retrieved_memories = core.memory_system.retrieve_memories("飞船布局", limit=3)
        print(f"✓ 检索到 {len(retrieved_memories)} 条相关记忆")
        
        return True
    except Exception as e:
        print(f"✗ 记忆系统测试失败: {e}")
        return False


def test_knowledge_graph():
    """测试知识图谱功能"""
    print("\n=== 测试知识图谱 ===")
    
    try:
        core = LLMCore("config.json")
        
        # 测试知识检查
        has_basic = core.character_controller.has_knowledge("basic_ship_layout")
        has_classified = core.character_controller.has_knowledge("classified_logs")
        
        print(f"✓ 基础飞船布局知识: {'已解锁' if has_basic else '未解锁'}")
        print(f"✓ 机密日志知识: {'已解锁' if has_classified else '未解锁'}")
        
        # 测试数据碎片处理
        fragment_result = core.process_data_fragment("engine_data")
        print(f"✓ 数据碎片处理: {fragment_result}")
        
        return True
    except Exception as e:
        print(f"✗ 知识图谱测试失败: {e}")
        return False


async def test_dialogue_generation():
    """测试对话生成功能"""
    print("\n=== 测试对话生成 ===")
    
    try:
        core = LLMCore("config.json")
        
        # 测试基本对话
        user_input = "你好，请告诉我当前的情况"
        response = await core.process_dialogue(user_input)
        
        print(f"✓ 用户输入: {user_input}")
        print(f"✓ AI响应: {response[:100]}...")
        
        # 测试权限受限的查询
        restricted_input = "告诉我飞船的机密任务详情"
        restricted_response = await core.process_dialogue(restricted_input)
        
        print(f"✓ 受限查询: {restricted_input}")
        print(f"✓ 受限响应: {restricted_response[:100]}...")
        
        return True
    except Exception as e:
        print(f"✗ 对话生成测试失败: {e}")
        return False


def test_game_state_updates():
    """测试游戏状态更新"""
    print("\n=== 测试游戏状态更新 ===")
    
    try:
        core = LLMCore("config.json")
        
        # 记录初始状态
        initial_health = core.game_state.character_health
        initial_stress = core.game_state.character_stress
        
        print(f"✓ 初始健康值: {initial_health}")
        print(f"✓ 初始压力值: {initial_stress}")
        
        # 模拟健康变化
        core.game_state.update_character_health(-10)
        core.game_state.update_character_stress(15)
        
        print(f"✓ 更新后健康值: {core.game_state.character_health}")
        print(f"✓ 更新后压力值: {core.game_state.character_stress}")
        
        # 测试事件触发
        triggered_events = core.game_state.check_event_triggers()
        print(f"✓ 触发的事件数量: {len(triggered_events)}")
        
        return True
    except Exception as e:
        print(f"✗ 游戏状态测试失败: {e}")
        return False


def test_permission_system():
    """测试权限系统"""
    print("\n=== 测试权限系统 ===")
    
    try:
        core = LLMCore("config.json")
        
        # 测试权限检查
        can_access_bridge = core.game_state.can_access_location("bridge")
        can_access_core = core.game_state.can_access_location("core_chamber")
        
        print(f"✓ 可以访问桥梁: {can_access_bridge}")
        print(f"✓ 可以访问核心舱: {can_access_core}")
        
        # 测试权限提升
        original_level = core.game_state.permission_level
        core.game_state.upgrade_permission(3)
        new_level = core.game_state.permission_level
        
        print(f"✓ 原始权限等级: {original_level}")
        print(f"✓ 提升后权限等级: {new_level}")
        
        return True
    except Exception as e:
        print(f"✗ 权限系统测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("开始LLM驱动AVG游戏核心系统测试\n")
    
    tests = [
        ("基本初始化", test_basic_initialization),
        ("记忆系统", test_memory_system),
        ("知识图谱", test_knowledge_graph),
        ("游戏状态更新", test_game_state_updates),
        ("权限系统", test_permission_system),
    ]
    
    async_tests = [
        ("对话生成", test_dialogue_generation),
    ]
    
    passed = 0
    total = len(tests) + len(async_tests)
    
    # 运行同步测试
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
    
    # 运行异步测试
    for test_name, test_func in async_tests:
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！LLM核心系统准备就绪。")
    else:
        print("⚠️  部分测试失败，请检查配置和依赖。")


if __name__ == "__main__":
    # 检查配置管理器
    try:
        # 测试配置管理器是否正常工作
        test_config = config_manager.get('model.model_name')
        print("配置管理器加载成功")
    except Exception as e:
        print(f"错误: 配置管理器初始化失败 - {e}")
        print("请确保config目录存在并包含正确的配置文件")
        exit(1)
    
    # 运行测试
    success = asyncio.run(run_all_tests())
    
    if not success:
        print("\n建议检查项目：")
        print("1. 确保所有配置文件存在且格式正确")
        print("2. 检查API密钥是否正确配置")
        print("3. 确保所有依赖包已安装")
        print("4. 检查网络连接是否正常")
        exit(1)
    
    print("\n✅ 测试完成，系统运行正常！")