#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制台UI模块

负责游戏的用户界面显示和用户输入处理，
与游戏操作处理模块分离，提供清晰的界面交互。

Author: AI Assistant
Date: 2024
"""

import os
import sys
from typing import Dict, Any
from llm_core import GameState, CharacterState, LLMCore


class GameUI:
    """游戏用户界面类"""
    
    def __init__(self):
        self.width = 80
        self.separator = "=" * self.width
        self.thin_separator = "-" * self.width
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_title(self):
        """打印游戏标题"""
        title = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🚀 深空迷航：记忆碎片 🚀                          ║
║                        LLM驱动的科幻文字冒险游戏                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(title)
    
    def print_separator(self, thick=True):
        """打印分隔线"""
        print(self.separator if thick else self.thin_separator)
    
    def print_status(self, game_state: GameState, character_state: CharacterState):
        """打印游戏状态"""
        print(f"\n📊 状态信息")
        print(self.thin_separator)
        print(f"🏥 健康: {game_state.character_health:.1f}%  😰 压力: {game_state.character_stress:.1f}%")
        print(f"⚡ 能量: {character_state.energy:.1f}%  😊 心情: {character_state.mood}")
        print(f"🔑 权限等级: {game_state.permission_level}  📍 位置: {game_state.current_location}")
        print(f"💾 数据碎片: {len(game_state.data_fragments)}个  ⏰ 游戏时间: {game_state.time_elapsed}分钟")
        if game_state.events_triggered:
            print(f"⚡ 最近事件: {', '.join(game_state.events_triggered[-3:])}")
    
    def print_detailed_status(self, game_state: GameState, character_state: CharacterState, llm_core: LLMCore):
        """打印详细状态信息"""
        print(f"\n📊 详细状态信息")
        print(self.separator)
        
        # 角色状态
        print(f"👤 角色状态:")
        print(f"  姓名: {character_state.name}")
        print(f"  健康: {character_state.health:.1f}%")
        print(f"  压力: {character_state.stress:.1f}%")
        print(f"  能量: {character_state.energy:.1f}%")
        print(f"  心情: {character_state.mood}")
        print(f"  位置: {character_state.location}")
        
        # 游戏状态
        print(f"\n🎮 游戏状态:")
        print(f"  权限等级: {game_state.permission_level}")
        print(f"  当前位置: {game_state.current_location}")
        print(f"  游戏时间: {game_state.time_elapsed}分钟")
        print(f"  数据碎片: {len(game_state.data_fragments)}个")
        
        # 剧情状态
        if hasattr(llm_core, 'script_constrainer'):
            try:
                story_context = llm_core.get_current_story_context()
                print(f"\n📖 剧情状态:")
                print(f"  当前节点: {story_context.get('title', '未知')}")
                print(f"  节点描述: {story_context.get('description', '无描述')[:50]}...")
                
                branches = llm_core.get_available_branches()
                if branches:
                    print(f"  可用分支: {len(branches)}个")
            except Exception as e:
                print(f"\n📖 剧情状态: 获取失败 ({e})")
        
        # 记忆系统状态
        if hasattr(llm_core, 'memory_system'):
            try:
                memory_count = len(llm_core.memory_system.long_term_memory)
                print(f"\n🧠 记忆系统:")
                print(f"  长期记忆: {memory_count}条")
                print(f"  对话缓存: {len(llm_core.memory_system.dialogue_cache)}条")
            except Exception as e:
                print(f"\n🧠 记忆系统: 获取失败 ({e})")
    
    def print_help(self):
        """打印帮助信息"""
        help_text = """
🎮 游戏帮助 - 自然语言交互

🗣️ 自然语言输入:
  你可以用自然语言与游戏交互，例如：
  - '看看周围' 或 '观察环境' - 查看当前位置
  - '去货舱' 或 '移动到货舱' - 移动到指定地点
  - '拾取手电筒' 或 '捡起工具' - 拾取物品
  - '使用钥匙' 或 '打开门' - 使用物品
  - '查看物品栏' 或 '我有什么' - 检查物品
  - '我的状态如何' - 查看角色状态

💬 对话交流:
  - '你好，我想了解这里的情况'
  - '告诉我关于这艘飞船的事情'
  - '我应该去哪里寻找线索？'
  - '这个物品有什么用？'

⚙️ 系统命令:
  help, h          - 显示此帮助信息
  quit, exit, q    - 退出游戏
  save [名称]      - 保存游戏
  load [名称]      - 加载游戏

💡 游戏提示:
  - AI会理解你的自然语言输入并执行相应动作
  - 尝试用不同的方式表达同一个意思
  - 游戏会自动保存进度
  - 探索环境，收集线索，推进剧情
        """
        print(help_text)
    
    def print_message(self, message: str, prefix: str = ""):
        """打印消息"""
        if prefix:
            print(f"{prefix} {message}")
        else:
            print(message)
    
    def get_input(self, prompt: str = "\n> ") -> str:
        """获取用户输入"""
        try:
            return input(prompt).strip()
        except KeyboardInterrupt:
            print("\n\n👋 游戏已退出")
            sys.exit(0)
        except EOFError:
            return "quit"
    
    def show_intro(self):
        """显示游戏介绍"""
        self.clear_screen()
        self.print_title()
        print("\n🎮 欢迎来到 AI 驱动的文字冒险游戏！")
        print("\n📖 游戏说明:")
        print("  • 这是一个基于人工智能的互动文字冒险游戏")
        print("  • 你可以使用自然语言与游戏世界互动")
        print("  • 输入 'help' 查看可用命令")
        print("  • 输入 'quit' 退出游戏")
        print("\n🌟 开始你的冒险之旅吧！")
        self.print_separator()
        return True
    
    async def show_story_status(self, core):
        """显示当前剧情状态"""
        try:
            if hasattr(core, 'script_constrainer') and core.script_constrainer:
                current_node = core.script_constrainer.get_current_story_node(core.game_state)
                if current_node:
                    print(f"\n📖 当前剧情节点: {current_node.id}")
                    print(f"📝 节点标题: {current_node.title}")
                    print(f"📄 节点描述: {current_node.description}")
                    print(f"🎭 角色处境: {current_node.character_situation}")
                    if current_node.branches:
                        print(f"🌿 可用分支: {len(current_node.branches)}个")
                else:
                    print("\n📖 当前没有活跃的剧情节点")
            else:
                print("\n📖 剧本框架未初始化")
        except Exception as e:
            print(f"\n❌ 获取剧情状态失败: {e}")
    
    async def show_story_branches(self, core):
        """显示可用的剧情分支"""
        try:
            if hasattr(core, 'script_constrainer') and core.script_constrainer:
                available_branches = core.script_constrainer.get_available_branches(
                    core.character_state, core.game_state
                )
                if available_branches:
                    print("\n🌿 可用剧情分支:")
                    for i, branch in enumerate(available_branches, 1):
                        branch_id = branch.get('id', f'branch_{i}')
                        description = branch.get('description', '未知分支')
                        target_node = branch.get('target_node_id', '未知目标')
                        print(f"  {i}. [{branch_id}] {description} -> {target_node}")
                else:
                    print("\n🌿 当前没有可用的剧情分支")
            else:
                print("\n🌿 剧本框架未初始化")
        except Exception as e:
            print(f"\n❌ 获取剧情分支失败: {e}")
    
    async def show_story_progress(self, core):
        """显示剧情进度"""
        try:
            if hasattr(core, 'script_constrainer') and core.script_constrainer:
                visited_nodes = getattr(core.script_constrainer, 'visited_nodes', set())
                total_nodes = len(core.script_constrainer.story_nodes)
                progress = len(visited_nodes) / total_nodes * 100 if total_nodes > 0 else 0
                
                print(f"\n📊 剧情进度: {len(visited_nodes)}/{total_nodes} ({progress:.1f}%)")
                print(f"📍 已访问节点: {', '.join(sorted(visited_nodes)) if visited_nodes else '无'}")
            else:
                print("\n📊 剧本框架未初始化")
        except Exception as e:
            print(f"\n❌ 获取剧情进度失败: {e}")
    

    def show_knowledge_status(self, knowledge_base: Dict[str, Any], character_controller, game_state: GameState):
        """显示当前知识状态"""
        try:
            print("\n🧠 知识库状态:")
            print(self.thin_separator)
            
            # 从配置文件获取知识项目
            unlocked_count = 0
            total_count = len(knowledge_base)
            
            if not knowledge_base:
                print("  ⚠️ 未找到知识库配置")
                return
            
            # 按权限等级排序显示知识项目
            sorted_knowledge = sorted(
                knowledge_base.items(),
                key=lambda x: x[1].get('required_permission', 1)
            )
            
            for knowledge_id, knowledge_info in sorted_knowledge:
                has_knowledge = character_controller.has_knowledge(knowledge_id)
                status = "✅ 已解锁" if has_knowledge else "🔒 未解锁"
                
                # 获取知识内容和权限要求
                content = knowledge_info.get('content', knowledge_id)
                required_permission = knowledge_info.get('required_permission', 1)
                
                # 显示知识状态，包含权限要求
                permission_info = f"(需要权限: {required_permission})"
                print(f"  {content}: {status} {permission_info}")
                
                if has_knowledge:
                    unlocked_count += 1
            
            # 显示完成度统计
            completion_rate = (unlocked_count / total_count * 100) if total_count > 0 else 0
            print(f"\n📊 知识完成度: {unlocked_count}/{total_count} ({completion_rate:.1f}%)")
            print(f"🔑 当前权限等级: {game_state.permission_level}")
            
        except Exception as e:
            print(f"❌ 无法显示知识状态: {e}")