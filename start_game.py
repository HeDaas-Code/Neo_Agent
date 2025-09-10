#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM驱动的AVG文字冒险游戏

基于LLM核心系统的交互式文字冒险游戏，玩家通过文本输入与AI角色对话，
探索飞船、收集信息、解开谜题，体验沉浸式的科幻冒险故事。

Author: AI Assistant
Date: 2024
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from llm_core import (
    LLMCore, GameState, CharacterState, StoryNode,
    CognitionResult, MemoryResult, UnderstandingResult,
    DecisionResult, ExecutionResult
)
from config_manager import config_manager


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


class SaveSystem:
    """存档系统"""
    
    def __init__(self, save_dir: str = "./saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
    
    def save_game(self, game_state: GameState, character_state: CharacterState, 
                  save_name: str = None) -> bool:
        """保存游戏"""
        if not save_name:
            save_name = f"autosave_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'game_state': {
                'permission_level': game_state.permission_level,
                'data_fragments': game_state.data_fragments,
                'current_location': game_state.current_location,
                'time_elapsed': game_state.time_elapsed,
                'events_triggered': game_state.events_triggered,
                'character_health': game_state.character_health,
                'character_stress': game_state.character_stress
            },
            'character_state': {
                'name': character_state.name,
                'health': character_state.health,
                'stress': character_state.stress,
                'energy': character_state.energy,
                'mood': character_state.mood,
                'location': character_state.location,
                'permissions': character_state.permissions
            }
        }
        
        try:
            save_file = self.save_dir / f"{save_name}.json"
            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def load_game(self, save_name: str) -> Optional[Dict[str, Any]]:
        """加载游戏"""
        try:
            save_file = self.save_dir / f"{save_name}.json"
            if not save_file.exists():
                return None
            
            with open(save_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return None
    
    def list_saves(self) -> List[str]:
        """列出所有存档"""
        saves = []
        for save_file in self.save_dir.glob("*.json"):
            saves.append(save_file.stem)
        return sorted(saves)


class AVGGame:
    """AVG游戏主类"""
    
    def __init__(self):
        self.ui = GameUI()
        self.save_system = SaveSystem()
        self.core = None
        self.running = False
        self.inventory = []
        
        # 从配置文件加载游戏数据
        self.config_dir = Path("e:\\项目（已开同步）\\Project\\config")
        self.locations = self._load_locations()
        self.knowledge_base = self._load_knowledge_base()
        self.character_config = self._load_character_config()
        self.game_config = self._load_game_config()
    
    def _load_locations(self) -> Dict[str, Any]:
        """从game.json加载地点配置"""
        try:
            game_config_path = self.config_dir / "game.json"
            with open(game_config_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
            locations = game_data.get('game_locations', {})
            if locations:
                print(f"✅ 成功加载 {len(locations)} 个地点配置")
                return locations
            else:
                print("⚠️ 配置文件中未找到game_locations，使用默认配置")
                return self._get_default_locations()
        except Exception as e:
            print(f"⚠️ 加载地点配置失败: {e}，使用默认配置")
            return self._get_default_locations()
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """从knowledge.json加载知识库配置"""
        try:
            knowledge_config_path = self.config_dir / "knowledge.json"
            with open(knowledge_config_path, 'r', encoding='utf-8') as f:
                knowledge_data = json.load(f)
            knowledge_base = knowledge_data.get('knowledge_base', {})
            if knowledge_base:
                print(f"✅ 成功加载 {len(knowledge_base)} 个知识项目")
                return knowledge_base
            else:
                print("⚠️ 配置文件中未找到knowledge_base，使用默认配置")
                return {}
        except Exception as e:
            print(f"⚠️ 加载知识库配置失败: {e}，使用默认配置")
            return {}
    
    def _load_character_config(self) -> Dict[str, Any]:
        """从character.json加载角色配置"""
        try:
            character_config_path = self.config_dir / "character.json"
            with open(character_config_path, 'r', encoding='utf-8') as f:
                character_data = json.load(f)
            if character_data:
                print(f"✅ 成功加载角色配置: {character_data.get('name', '未知角色')}")
                return character_data
            else:
                print("⚠️ 角色配置文件为空，使用默认配置")
                return {}
        except Exception as e:
            print(f"⚠️ 加载角色配置失败: {e}，使用默认配置")
            return {}
    
    def _load_game_config(self) -> Dict[str, Any]:
        """从game.json加载游戏配置"""
        try:
            game_config_path = self.config_dir / "game.json"
            with open(game_config_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
            if game_data:
                events_count = len(game_data.get('events', {}))
                fragments_count = len(game_data.get('data_fragments', {}))
                print(f"✅ 成功加载游戏配置: {events_count}个事件, {fragments_count}个数据碎片")
                return game_data
            else:
                print("⚠️ 游戏配置文件为空，使用默认配置")
                return {}
        except Exception as e:
            print(f"⚠️ 加载游戏配置失败: {e}，使用默认配置")
            return {}
    
    def _get_default_locations(self) -> Dict[str, Any]:
        """获取默认地点配置（作为后备）"""
        return {
            "bridge": {
                "name": "舰桥",
                "description": "飞船的指挥中心，各种控制台闪烁着微弱的光芒。主屏幕显示着星图，但大部分系统似乎处于待机状态。",
                "items": ["导航日志", "通讯记录"],
                "exits": ["工程舱", "生活区"]
            },
            "engineering": {
                "name": "工程舱",
                "description": "飞船的心脏，巨大的反应堆在这里安静地运转。各种管道和线缆纵横交错，空气中弥漫着淡淡的臭氧味。",
                "items": ["维修工具", "能源电池", "技术手册"],
                "exits": ["舰桥", "货舱"]
            },
            "living_quarters": {
                "name": "生活区",
                "description": "船员的休息区域，几个休眠舱整齐排列。墙上的个人物品暗示着这里曾经有人居住。",
                "items": ["个人日记", "医疗包"],
                "exits": ["舰桥"]
            },
            "cargo_bay": {
                "name": "货舱",
                "description": "宽敞的货物存储区，大部分货箱都被密封着。角落里有一些散落的设备和神秘的容器。",
                "items": ["神秘容器", "扫描设备"],
                "exits": ["工程舱"]
            }
        }
    
    async def initialize(self):
        """初始化游戏"""
        try:
            # 初始化LLM核心系统
            self.core = LLMCore()
            print("✅ LLM核心系统初始化成功")
            
            # 设置初始角色状态（如果需要自定义）
            if self.character_config:
                character_name = self.character_config.get('name', '艾莉克斯')
                self.core.character_state.name = character_name
                print(f"✅ 角色设置完成: {character_name}")
            
            # 设置初始游戏状态
            if self.game_config:
                initial_location = self.game_config.get('initial_location', 'engineering')
                self.core.game_state.current_location = initial_location
                self.core.character_state.location = initial_location
                print(f"✅ 初始位置设置: {initial_location}")
            
            # 验证五阶段架构
            print("🔍 验证五阶段架构...")
            test_input = "系统自检"
            try:
                # 测试认知阶段
                cognition_result = await self.core._cognition_stage(test_input)
                print(f"  ✓ 认知阶段正常，置信度: {cognition_result.confidence_score}")
                
                # 测试记忆阶段
                memory_result = await self.core._memory_stage(cognition_result, test_input)
                print(f"  ✓ 记忆阶段正常，知识节点: {len(memory_result.knowledge_graph_nodes)}")
                
                # 测试理解阶段
                understanding_result = await self.core._understanding_stage(cognition_result, memory_result, test_input)
                print(f"  ✓ 理解阶段正常")
                
                # 测试决策阶段
                decision_result = await self.core._decision_stage(cognition_result, memory_result, understanding_result)
                print(f"  ✓ 决策阶段正常，策略: {decision_result.dialogue_strategy}")
                
                print("✅ 五阶段架构验证完成")
                
            except Exception as stage_error:
                print(f"⚠️ 五阶段架构验证失败: {stage_error}")
                print("游戏仍可运行，但可能存在功能限制")
            
            # 验证剧本框架
            if hasattr(self.core, 'script_constrainer'):
                try:
                    story_nodes_count = len(self.core.script_constrainer.story_nodes)
                    print(f"✅ 剧本框架加载完成，节点数: {story_nodes_count}")
                except Exception as script_error:
                    print(f"⚠️ 剧本框架验证失败: {script_error}")
            
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_intro(self):
        """显示游戏开场"""
        intro_text = """


💡 输入 'help' 查看游戏指令，输入任何文字开始与AI对话。
        """
        print(intro_text)
        return True
    
    async def _show_story_status(self):
        """显示当前剧情状态"""
        try:
            if hasattr(self.core, 'script_constrainer') and self.core.script_constrainer:
                current_node = self.core.script_constrainer.get_current_story_node(self.core.game_state)
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

    async def _show_story_branches(self):
        """显示可用的剧情分支"""
        try:
            if hasattr(self.core, 'script_constrainer') and self.core.script_constrainer:
                available_branches = self.core.script_constrainer.get_available_branches(
                    self.core.character_state, self.core.game_state
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

    async def _show_story_progress(self):
        """显示剧情进度"""
        try:
            if hasattr(self.core, 'script_constrainer') and self.core.script_constrainer:
                visited_nodes = getattr(self.core.script_constrainer, 'visited_nodes', set())
                total_nodes = len(self.core.script_constrainer.story_nodes)
                progress = len(visited_nodes) / total_nodes * 100 if total_nodes > 0 else 0
                
                print(f"\n📊 剧情进度: {len(visited_nodes)}/{total_nodes} ({progress:.1f}%)")
                print(f"📍 已访问节点: {', '.join(sorted(visited_nodes)) if visited_nodes else '无'}")
            else:
                print("\n📊 剧本框架未初始化")
        except Exception as e:
            print(f"\n❌ 获取剧情进度失败: {e}")

    async def _select_story_branch(self, branch_id: str):
        """选择剧情分支"""
        try:
            if hasattr(self.core, 'script_constrainer') and self.core.script_constrainer:
                # 尝试推进到指定分支
                success = self.core.script_constrainer.advance_to_branch(
                    branch_id, self.core.character_state, self.core.game_state
                )
                if success:
                    print(f"\n✅ 已切换到剧情分支: {branch_id}")
                    await self._show_story_status()  # 显示新节点状态
                else:
                    print(f"\n❌ 无法切换到分支 {branch_id}，可能不满足条件或分支不存在")
            else:
                print("\n❌ 剧本框架未初始化")
        except Exception as e:
            print(f"\n❌ 选择剧情分支失败: {e}")
    
    async def process_command(self, user_input: str) -> bool:
        """处理用户命令"""
        command = user_input.lower().strip()
        
        # 退出命令
        if command in ['quit', 'exit', 'q']:
            return False
        
        # 帮助命令
        elif command in ['help', 'h']:
            self.ui.print_help()
        
        # 状态命令
        elif command in ['status', 'st']:
            self.ui.print_status(self.core.game_state, self.core.character_state)
            print(f"\n📦 物品栏: {', '.join(self.inventory) if self.inventory else '空'}")
        
        # 详细状态命令
        elif command in ['detail', 'dt']:
            self.ui.print_detailed_status(self.core.game_state, self.core.character_state, self.core)
        
        # 详细模式切换
        elif command in ['verbose', 'v']:
            self.toggle_verbose_mode()
        
        # 物品栏命令
        elif command in ['inventory', 'inv']:
            if self.inventory:
                print(f"\n📦 你的物品: {', '.join(self.inventory)}")
            else:
                print("\n📦 你的物品栏是空的")
        
        # 知识库命令
        elif command in ['knowledge', 'know', 'k']:
            self.show_knowledge_status()
        
        # 剧情状态命令
        elif command in ['story', 's']:
            await self._show_story_status()
        
        # 剧情分支命令
        elif command in ['branches', 'br']:
            await self._show_story_branches()
        
        # 剧情进度命令
        elif command in ['progress', 'pr']:
            await self._show_story_progress()
        
        # 选择分支命令
        elif command.startswith('select '):
            branch_id = command[7:].strip()
            await self._select_story_branch(branch_id)
        
        # 观察命令
        elif command in ['look', 'l']:
            await self.describe_location()
        
        # 保存命令
        elif command.startswith('save'):
            parts = command.split()
            save_name = parts[1] if len(parts) > 1 else None
            if self.save_system.save_game(self.core.game_state, self.core.character_state, save_name):
                print(f"💾 游戏已保存: {save_name or 'autosave'}")
        
        # 加载命令
        elif command.startswith('load'):
            parts = command.split()
            if len(parts) > 1:
                await self.load_game(parts[1])
            else:
                saves = self.save_system.list_saves()
                if saves:
                    print(f"\n💾 可用存档: {', '.join(saves)}")
                else:
                    print("\n💾 没有找到存档文件")
        
        # 移动命令
        elif command.startswith('go '):
            destination = command[3:].strip()
            await self.move_to_location(destination)
        
        # 检查命令
        elif command.startswith('examine '):
            item = command[8:].strip()
            await self.examine_item(item)
        
        # 使用命令
        elif command.startswith('use '):
            item = command[4:].strip()
            await self.use_item(item)
        
        # 拾取命令
        elif command.startswith('take '):
            item = command[5:].strip()
            await self.take_item(item)
        
        # 对话相关命令
        elif command.startswith('talk '):
            topic = command[5:].strip()
            await self.process_dialogue(f"我想谈论{topic}")
        
        elif command.startswith('ask '):
            question = command[4:].strip()
            await self.process_dialogue(f"我想问：{question}")
        
        elif command.startswith('tell '):
            info = command[5:].strip()
            await self.process_dialogue(f"我想告诉你：{info}")
        
        # 其他输入作为对话处理
        else:
            await self.process_dialogue(user_input)
        
        return True
    
    async def describe_location(self):
        """描述当前位置"""
        current_loc = self.core.game_state.current_location
        if current_loc in self.locations:
            loc_info = self.locations[current_loc]
            print(f"\n📍 {loc_info['name']}")
            print(self.ui.thin_separator)
            print(loc_info['description'])
            
            if loc_info['items']:
                print(f"\n🔍 你看到: {', '.join(loc_info['items'])}")
            
            if loc_info['exits']:
                print(f"\n🚪 可前往: {', '.join(loc_info['exits'])}")
        else:
            # 使用AI生成位置描述
            response = await self.core.process_dialogue(f"描述我当前所在的{current_loc}")
            print(f"\n📍 {current_loc}")
            print(self.ui.thin_separator)
            print(response)
    
    async def move_to_location(self, destination: str):
        """移动到指定位置"""
        # 检查权限
        if not self.core.game_state.can_access_location(destination.lower()):
            print(f"❌ 权限不足，无法进入{destination}")
            return
        
        # 更新位置
        old_location = self.core.game_state.current_location
        self.core.game_state.current_location = destination.lower()
        self.core.character_state.location = destination.lower()
        
        print(f"🚶 你从{old_location}来到了{destination}")
        await self.describe_location()
        
        # 更新游戏时间
        self.core.game_state.time_elapsed += 5
    
    async def examine_item(self, item: str):
        """检查物品"""
        response = await self.core.process_dialogue(f"仔细检查{item}")
        print(f"\n🔍 检查{item}:")
        print(response)
    
    async def use_item(self, item: str):
        """使用物品"""
        if item in self.inventory:
            response = await self.core.process_dialogue(f"使用{item}")
            print(f"\n🔧 使用{item}:")
            print(response)
            
            # 某些物品使用后可能触发特殊效果
            if "医疗包" in item:
                self.core.game_state.update_character_health(20)
                print("💊 健康状况有所改善")
        else:
            print(f"❌ 你没有{item}")
    
    async def take_item(self, item: str):
        """拾取物品"""
        current_loc = self.core.game_state.current_location
        if current_loc in self.locations:
            loc_items = self.locations[current_loc]['items']
            if item in loc_items:
                self.inventory.append(item)
                loc_items.remove(item)
                print(f"✅ 你拾取了{item}")
                
                # 某些物品可能是数据碎片
                if "日志" in item or "记录" in item or "数据" in item:
                    fragment_id = f"fragment_{len(self.core.game_state.data_fragments)}"
                    self.core.game_state.data_fragments.append(fragment_id)
                    print(f"💾 发现数据碎片！当前共有{len(self.core.game_state.data_fragments)}个")
                    
                    # 处理数据碎片，可能解锁新知识
                    await self.process_knowledge_fragment(item)
            else:
                print(f"❌ 这里没有{item}")
        else:
            print(f"❌ 这里没有{item}")
    
    async def process_dialogue(self, user_input: str):
        """处理对话"""
        print("\n🤖 AI正在思考...")
        
        try:
            # 存储用户输入到记忆系统
            self.core.memory_system.store_memory(
                user_input,
                {
                    'type': 'user_input',
                    'timestamp': int(time.time()),
                    'location': self.core.game_state.current_location,
                    'permission_level': self.core.game_state.permission_level
                }
            )
            
            # 如果启用了详细模式，显示各阶段处理信息
            if getattr(self, 'verbose_mode', False):
                print("🔄 正在处理对话...")
                print("  🧠 认知阶段: 分析输入内容...")
                cognition_result = await self.core._cognition_stage(user_input)
                print(f"    ✓ 置信度: {cognition_result.confidence_score}")
                
                print("  🧠 记忆阶段: 检索相关信息...")
                memory_result = await self.core._memory_stage(cognition_result, user_input)
                print(f"    ✓ 知识节点: {len(memory_result.knowledge_graph_nodes)}")
                
                print("  🧠 理解阶段: 分析上下文...")
                understanding_result = await self.core._understanding_stage(cognition_result, memory_result, user_input)
                
                print("  🧠 决策阶段: 制定响应策略...")
                decision_result = await self.core._decision_stage(cognition_result, memory_result, understanding_result)
                print(f"    ✓ 策略: {decision_result.dialogue_strategy}")
                
                print("  🧠 执行阶段: 生成响应...")
            
            # 生成AI响应
            response = await self.core.process_dialogue(user_input)
            
            print(f"\n🤖 艾莉克斯: {response}")
            
            # 存储AI响应到记忆系统
            self.core.memory_system.store_memory(
                response,
                {
                    'type': 'ai_response',
                    'timestamp': int(time.time()),
                    'location': self.core.game_state.current_location,
                    'character': '艾莉克斯'
                }
            )
            
            # 更新游戏时间
            self.core.game_state.time_elapsed += 2
            
            # 检查事件触发
            triggered_events = self.core.game_state.check_event_triggers()
            if triggered_events:
                print(f"\n⚡ 触发事件: {', '.join(triggered_events)}")
            
            # 检查剧情推进
            await self._check_story_progression(user_input, response)
            
        except Exception as e:
            print(f"❌ 对话处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_story_progression(self, user_input: str, ai_response: str):
        """检查剧情推进"""
        try:
            if hasattr(self.core, 'script_constrainer') and self.core.script_constrainer:
                # 检查当前节点的完成条件
                current_node = self.core.script_constrainer.get_current_story_node(self.core.game_state)
                if current_node:
                    # 简单的关键词匹配来判断剧情推进
                    progression_keywords = [
                        '完成', '结束', '离开', '前往', '决定', '选择',
                        '同意', '拒绝', '接受', '获得', '发现'
                    ]
                    
                    user_lower = user_input.lower()
                    response_lower = ai_response.lower()
                    
                    # 检查是否包含推进关键词
                    has_progression = any(
                        keyword in user_lower or keyword in response_lower 
                        for keyword in progression_keywords
                    )
                    
                    # 获取可用分支
                    available_branches = self.core.script_constrainer.get_available_branches(
                        self.core.character_state, self.core.game_state
                    )
                    
                    if has_progression and available_branches:
                        print("\n🎭 检测到剧情推进机会！")
                        print("💡 输入 'branches' 查看可用的剧情分支")
                        
                        # 自动推进到下一个节点（如果只有一个选择）
                        if len(available_branches) == 1:
                            branch = available_branches[0]
                            branch_id = branch.get('id')
                            if branch_id:
                                success = self.core.script_constrainer.advance_to_branch(
                                    branch_id, self.core.character_state, self.core.game_state
                                )
                                if success:
                                    target_node = branch.get('target_node_id', '未知节点')
                                    print(f"🎬 自动推进到下一剧情节点: {target_node}")
                                
        except Exception as e:
            print(f"⚠️ 剧情推进检查失败: {e}")
    
    def toggle_verbose_mode(self):
        """切换详细模式"""
        self.verbose_mode = not getattr(self, 'verbose_mode', False)
        status = "开启" if self.verbose_mode else "关闭"
        print(f"🔧 详细模式已{status}")
        return self.verbose_mode
    
    async def process_knowledge_fragment(self, item: str):
        """处理知识碎片，可能解锁新知识"""
        try:
            # 根据物品类型处理不同的数据碎片
            fragment_type = None
            if "导航" in item:
                fragment_type = "navigation_data"
            elif "通讯" in item:
                fragment_type = "communication_logs"
            elif "技术" in item or "维修" in item:
                fragment_type = "technical_manual"
            elif "个人" in item:
                fragment_type = "personal_logs"
            elif "神秘" in item:
                fragment_type = "classified_data"
            
            if fragment_type:
                # 处理数据碎片
                fragment_result = self.core.process_data_fragment(fragment_type)
                print(f"🧠 数据分析: {fragment_result}")
                
                # 检查是否解锁了新知识
                await self.check_knowledge_unlock(fragment_type)
        except Exception as e:
            print(f"⚠️ 数据碎片处理失败: {e}")
    
    async def check_knowledge_unlock(self, fragment_type: str):
        """检查知识解锁情况"""
        try:
            # 从配置文件检查知识状态
            knowledge_status = []
            unlocked_count = 0
            
            for knowledge_id, knowledge_info in self.knowledge_base.items():
                if self.core.character_controller.has_knowledge(knowledge_id):
                    knowledge_status.append(knowledge_info.get('content', knowledge_id))
                    unlocked_count += 1
            
            if knowledge_status:
                print(f"🔓 已解锁知识: {', '.join(knowledge_status[:3])}")
                if len(knowledge_status) > 3:
                    print(f"   ... 以及其他 {len(knowledge_status) - 3} 项知识")
            
            # 根据解锁的知识数量和权限要求提升权限等级
            current_permission = self.core.game_state.permission_level
            
            # 检查是否满足权限提升条件
            if unlocked_count >= 2 and current_permission < 3:
                self.core.game_state.upgrade_permission(3)
                print(f"⬆️ 权限等级提升至: {self.core.game_state.permission_level}")
            elif unlocked_count >= 4 and current_permission < 5:
                self.core.game_state.upgrade_permission(5)
                print(f"⬆️ 权限等级提升至: {self.core.game_state.permission_level}")
                
        except Exception as e:
            print(f"⚠️ 知识检查失败: {e}")
    
    def show_knowledge_status(self):
        """显示当前知识状态"""
        try:
            print("\n🧠 知识库状态:")
            print(self.ui.thin_separator)
            
            # 从配置文件获取知识项目
            unlocked_count = 0
            total_count = len(self.knowledge_base)
            
            if not self.knowledge_base:
                print("  ⚠️ 未找到知识库配置")
                return
            
            # 按权限等级排序显示知识项目
            sorted_knowledge = sorted(
                self.knowledge_base.items(),
                key=lambda x: x[1].get('required_permission', 1)
            )
            
            for knowledge_id, knowledge_info in sorted_knowledge:
                has_knowledge = self.core.character_controller.has_knowledge(knowledge_id)
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
            print(f"🔑 当前权限等级: {self.core.game_state.permission_level}")
            
        except Exception as e:
            print(f"❌ 无法显示知识状态: {e}")
    
    async def load_game(self, save_name: str):
        """加载游戏"""
        save_data = self.save_system.load_game(save_name)
        if save_data:
            # 恢复游戏状态
            game_data = save_data['game_state']
            char_data = save_data['character_state']
            
            self.core.game_state.permission_level = game_data['permission_level']
            self.core.game_state.data_fragments = game_data['data_fragments']
            self.core.game_state.current_location = game_data['current_location']
            self.core.game_state.time_elapsed = game_data['time_elapsed']
            self.core.game_state.events_triggered = game_data['events_triggered']
            self.core.game_state.character_health = game_data['character_health']
            self.core.game_state.character_stress = game_data['character_stress']
            
            self.core.character_state.health = char_data['health']
            self.core.character_state.stress = char_data['stress']
            self.core.character_state.energy = char_data['energy']
            self.core.character_state.mood = char_data['mood']
            self.core.character_state.location = char_data['location']
            
            print(f"✅ 游戏已加载: {save_name}")
        else:
            print(f"❌ 找不到存档: {save_name}")
    
    async def run(self):
        """运行游戏主循环"""
        self.ui.clear_screen()
        self.ui.print_title()
        
        # 初始化游戏
        if not await self.initialize():
            return
        
        self.show_intro()
        self.running = True
        
        # 自动保存计数器
        auto_save_counter = 0
        
        while self.running:
            try:
                # 显示状态栏
                self.ui.print_separator(False)
                self.ui.print_status(self.core.game_state, self.core.character_state)
                
                # 获取用户输入
                user_input = self.ui.get_input()
                
                if not user_input:
                    continue
                
                # 处理命令
                should_continue = await self.process_command(user_input)
                if not should_continue:
                    break
                
                # 自动保存
                auto_save_counter += 1
                if auto_save_counter >= 10:
                    self.save_system.save_game(self.core.game_state, self.core.character_state)
                    auto_save_counter = 0
                
            except KeyboardInterrupt:
                print("\n\n👋 游戏已退出")
                break
            except Exception as e:
                print(f"\n❌ 游戏错误: {e}")
                print("游戏将继续运行...")
        
        # 退出时自动保存
        self.save_system.save_game(self.core.game_state, self.core.character_state, "exit_save")
        print("\n💾 游戏进度已自动保存")
        print("\n🌟 感谢游玩《深空迷航：记忆碎片》！")


async def main():
    """主函数"""
    game = AVGGame()
    await game.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 游戏已退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("请检查配置文件和依赖是否正确安装")