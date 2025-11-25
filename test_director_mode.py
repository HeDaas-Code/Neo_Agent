#!/usr/bin/env python
"""
导演模式测试脚本
演示时间线的创建和场景管理功能
"""

from chat_agent import ChatAgent
from director_mode import ScenarioType, TriggerType
import sys
import time


def test_create_timeline(agent):
    """测试创建时间线"""
    print("\n" + "="*60)
    print("测试 1: 创建时间线")
    print("="*60)
    
    # 创建时间线
    timeline = agent.create_director_timeline(
        name="角色扮演：校园生活",
        description="模拟智能体在校园中的一天生活"
    )
    
    print(f"✓ 时间线已创建")
    print(f"  - ID: {timeline.timeline_id[:8]}...")
    print(f"  - 名称: {timeline.name}")
    print(f"  - 描述: {timeline.description}")
    
    return timeline


def test_add_scenarios(agent, timeline):
    """测试添加场景"""
    print("\n" + "="*60)
    print("测试 2: 添加场景到时间线")
    print("="*60)
    
    # 场景1：早晨起床
    scenario1 = agent.add_scenario_to_director_timeline(
        timeline_id=timeline.timeline_id,
        name="早晨起床",
        description="阳光透过窗户照进房间，闹钟响起，新的一天开始了",
        scenario_type="environment",
        trigger_type="time",
        trigger_time=0,  # 立即触发
        content={
            'time_of_day': '早晨7:00',
            'mood': '宁静、舒适',
            'environment_hints': ['阳光', '闹钟', '被窝', '窗帘']
        },
        duration=5,
        auto_advance=True
    )
    print(f"✓ 场景1已添加: {scenario1.name}")
    
    # 场景2：问候对话
    scenario2 = agent.add_scenario_to_director_timeline(
        timeline_id=timeline.timeline_id,
        name="早安问候",
        description="用户可能会和你打招呼",
        scenario_type="dialogue",
        trigger_type="sequence",  # 上一个场景完成后触发
        content={
            'dialogue_hints': ['早安', '睡得好吗', '今天天气'],
            'expected_response_style': '活泼、亲切、略带困意'
        },
        duration=30,
        auto_advance=False  # 需要用户互动
    )
    print(f"✓ 场景2已添加: {scenario2.name}")
    
    # 场景3：情绪变化
    scenario3 = agent.add_scenario_to_director_timeline(
        timeline_id=timeline.timeline_id,
        name="期待新一天",
        description="逐渐清醒，对新的一天充满期待",
        scenario_type="emotion",
        trigger_type="sequence",
        content={
            'emotion': 'anticipation',
            'intensity': 0.7,
            'reason': '今天有期待已久的课程'
        },
        duration=3,
        auto_advance=True
    )
    print(f"✓ 场景3已添加: {scenario3.name}")
    
    # 场景4：准备出门
    scenario4 = agent.add_scenario_to_director_timeline(
        timeline_id=timeline.timeline_id,
        name="准备出门",
        description="换好衣服，整理书包，准备去学校",
        scenario_type="action",
        trigger_type="sequence",
        content={
            'action': '整理书包',
            'target': '课本和笔记',
            'manner': '仔细地检查每一样东西'
        },
        duration=10,
        auto_advance=True
    )
    print(f"✓ 场景4已添加: {scenario4.name}")
    
    print(f"\n时间线共有 {len(timeline.scenarios) + 4} 个场景")
    
    return [scenario1, scenario2, scenario3, scenario4]


def test_timeline_management(agent):
    """测试时间线管理功能"""
    print("\n" + "="*60)
    print("测试 3: 时间线管理功能")
    print("="*60)
    
    # 获取所有时间线
    timelines = agent.get_all_director_timelines()
    print(f"\n📋 时间线列表 (共{len(timelines)}个):")
    for i, tl in enumerate(timelines, 1):
        print(f"  {i}. {tl['name']}")
        print(f"     ID: {tl['timeline_id'][:8]}...")
        print(f"     场景数: {len(tl['scenarios'])}")
        print(f"     状态: {'激活' if tl['is_active'] else '未激活'}")
    
    # 获取导演模式统计
    stats = agent.get_director_statistics()
    print(f"\n📊 导演模式统计:")
    print(f"  - 总时间线数: {stats['total_timelines']}")
    print(f"  - 总场景数: {stats['total_scenarios']}")
    print(f"  - 是否运行中: {stats['is_running']}")


def test_sample_timeline(agent):
    """测试创建示例时间线"""
    print("\n" + "="*60)
    print("测试 4: 创建示例时间线")
    print("="*60)
    
    # 创建示例时间线
    sample_timeline = agent.create_sample_director_timeline()
    
    print(f"✓ 示例时间线已创建")
    print(f"  - 名称: {sample_timeline.name}")
    print(f"  - 场景数: {len(sample_timeline.scenarios)}")
    
    print("\n场景列表:")
    for i, scenario in enumerate(sample_timeline.scenarios, 1):
        print(f"  {i}. {scenario.name}")
        print(f"     类型: {scenario.scenario_type.value}")
        print(f"     触发: {scenario.trigger_type.value} @ {scenario.trigger_time}s")
    
    return sample_timeline


def test_timeline_execution(agent, timeline):
    """测试时间线执行（简化版，不等待完整执行）"""
    print("\n" + "="*60)
    print("测试 5: 时间线执行控制")
    print("="*60)
    
    # 启动时间线
    print("\n启动时间线...")
    success = agent.start_director_timeline(timeline.timeline_id)
    print(f"  启动结果: {'成功' if success else '失败'}")
    
    # 检查是否激活
    print(f"  导演模式激活: {agent.is_director_mode_active()}")
    
    # 等待一小段时间让场景触发
    print("\n等待场景触发...")
    time.sleep(2)
    
    # 获取当前场景上下文
    context = agent.get_current_scenario_context()
    if context:
        print(f"\n当前场景上下文:")
        scenario_data = context.get('scenario', {})
        print(f"  场景名称: {scenario_data.get('name', '无')}")
        print(f"  触发时间: {context.get('triggered_at', '无')}")
    
    # 暂停
    print("\n暂停时间线...")
    agent.pause_director_timeline()
    print(f"  暂停状态: {agent.director_mode.is_paused()}")
    
    # 恢复
    print("\n恢复时间线...")
    agent.resume_director_timeline()
    print(f"  暂停状态: {agent.director_mode.is_paused()}")
    
    # 停止
    print("\n停止时间线...")
    agent.stop_director_timeline()
    print(f"  导演模式激活: {agent.is_director_mode_active()}")


def main():
    print("="*60)
    print("Neo Agent 导演模式测试")
    print("="*60)
    
    # 初始化代理
    print("\n正在初始化 ChatAgent...")
    agent = ChatAgent()
    
    try:
        # 测试创建时间线
        timeline = test_create_timeline(agent)
        
        # 测试添加场景
        test_add_scenarios(agent, timeline)
        
        # 测试时间线管理
        test_timeline_management(agent)
        
        # 测试示例时间线
        sample_timeline = test_sample_timeline(agent)
        
        # 测试时间线执行
        test_timeline_execution(agent, sample_timeline)
        
        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)
        
        print("\n💡 提示:")
        print("  1. 启动 GUI: python gui_enhanced.py")
        print("  2. 打开「导演模式」标签页")
        print("  3. 创建或选择时间线")
        print("  4. 点击「开始时间线」启动角色扮演")
        print("  5. 在聊天窗口与智能体对话，体验场景驱动的对话")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
