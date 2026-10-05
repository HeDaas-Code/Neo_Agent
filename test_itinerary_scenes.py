"""测试日程驱动场景生成（Phase 3）。"""
import tempfile
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import Mock
import json

from neo_agent.storage import DiskStore
from neo_agent.runtime.itinerary import (
    SceneService,
    DailyItineraryService,
    ScheduleDecisionService,
    SceneScheduler
)


def test_initial_environment_idempotent():
    """测试初始环境只创建一次。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        scene_service = SceneService(store)
        
        # 第一次创建
        result1 = scene_service.ensure_initial_environment()
        
        assert result1["environment"]["id"] == "daily_start"
        assert result1["place"]["id"] == "daily_home"
        assert result1["area"]["id"] == "home_living"
        
        # 第二次调用应该返回相同的数据，不重复创建
        result2 = scene_service.ensure_initial_environment()
        
        assert result2["environment"]["id"] == result1["environment"]["id"]
        assert result2["place"]["id"] == result1["place"]["id"]
        assert result2["area"]["id"] == result1["area"]["id"]
        
        # 验证只有一个 place
        places = scene_service.places()
        assert len(places) == 1
        assert places[0]["id"] == "daily_home"
        
        print("✅ 初始环境幂等创建测试通过")


def test_scene_hierarchy():
    """测试场景层级：地点 → 区域 → 物体。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        scene_service = SceneService(store)
        scene_service.ensure_initial_environment()
        
        # 获取初始场景
        place = store.get_document("places", "daily_home")
        areas = scene_service.areas("daily_home")
        
        assert place is not None
        assert place["name"] == "家"
        assert len(areas) >= 1
        assert areas[0]["place_id"] == "daily_home"
        
        # 检查物体
        env_id = place["environment_id"]
        objects = store.environment_objects(env_id, visible_only=False)
        
        assert len(objects) >= 1
        assert any(obj["area_id"] == "home_living" for obj in objects)
        
        print("✅ 场景层级结构测试通过")


def test_current_scene_context():
    """测试当前场景上下文生成。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        scene_service = SceneService(store)
        scene_service.ensure_initial_environment()
        
        # 获取当前场景上下文
        context = scene_service.current_context()
        
        assert "当前场景" in context
        assert "家" in context or "日常起点" in context
        
        # 应该包含物体描述
        assert len(context) > 0
        
        print("✅ 场景上下文生成测试通过")


def test_scene_pool_matching():
    """测试场景池匹配逻辑。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        # 创建模拟模型
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps({
            "place_name": "图书馆",
            "place_description": "安静的学习场所",
            "tags": ["study", "quiet"],
            "area_name": "阅览室",
            "area_description": "有很多书架的房间",
            "objects": [
                {"name": "书架", "description": "摆满了书", "state": "整齐"}
            ]
        })
        mock_model.invoke.return_value = mock_response
        
        scene_service = SceneService(store, model=mock_model)
        scene_service.ensure_initial_environment()
        
        # 第一次：应该生成新场景
        result1 = scene_service.resolve_for_activity(
            purpose="学习",
            place_hint="图书馆",
            stable_key="test_activity_1"
        )
        
        assert result1["place"]["name"] == "图书馆" or result1["reused"] is True
        
        # 第二次：相同目的和提示，应该复用
        result2 = scene_service.resolve_for_activity(
            purpose="学习",
            place_hint="图书馆",
            stable_key="test_activity_2"
        )
        
        # 如果第一次成功生成了图书馆，第二次应该复用
        if result1["place"]["name"] == "图书馆":
            assert result2["place"]["id"] == result1["place"]["id"]
            assert result2["reused"] is True
        
        print("✅ 场景池匹配测试通过")


def test_daily_itinerary_structure():
    """测试每日行程生成的基础结构。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        # 使用 save_character 方法创建角色
        store.save_character("default", {
            "name": "林依",
            "personality": "活泼开朗的高中生",
            "world_view": "现代都市校园生活"
        })
        
        # 创建模拟模型
        mock_model = Mock()
        mock_response = Mock()
        
        # 模拟生成简单的一日行程
        tz = ZoneInfo("Asia/Shanghai")
        today = datetime.now(tz).date()
        
        mock_response.content = json.dumps({
            "summary": "普通的一天",
            "activities": [
                {
                    "title": "早晨阅读",
                    "description": "在家里看书",
                    "purpose": "放松和学习",
                    "start_at": datetime.combine(today, time(8, 0), tzinfo=tz).isoformat(),
                    "end_at": datetime.combine(today, time(9, 0), tzinfo=tz).isoformat(),
                    "place_name": "家",
                    "area_name": "起居室",
                    "tags": ["reading", "morning"]
                },
                {
                    "title": "午餐时间",
                    "description": "在家吃午饭",
                    "purpose": "用餐",
                    "start_at": datetime.combine(today, time(12, 0), tzinfo=tz).isoformat(),
                    "end_at": datetime.combine(today, time(13, 0), tzinfo=tz).isoformat(),
                    "place_name": "家",
                    "area_name": "起居室",
                    "tags": ["meal", "lunch"]
                }
            ]
        })
        mock_model.invoke.return_value = mock_response
        
        scene_service = SceneService(store, model=mock_model)
        itinerary_service = DailyItineraryService(store, model=mock_model, scene_service=scene_service)
        
        # 生成今日行程
        now = datetime.now(tz)
        result = itinerary_service.ensure_for_day(now=now, character={"name": "林依"})
        
        assert result is not None
        assert result["local_date"] == today.isoformat()
        assert result["timezone"] == "Asia/Shanghai"
        assert "schedule_ids" in result
        
        print("✅ 每日行程结构测试通过")


def test_itinerary_idempotent():
    """测试每日行程生成幂等。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        store.save_character("default", {
            "name": "林依",
            "personality": "活泼开朗的高中生"
        })
        
        mock_model = Mock()
        mock_response = Mock()
        
        tz = ZoneInfo("Asia/Shanghai")
        today = datetime.now(tz).date()
        
        mock_response.content = json.dumps({
            "summary": "测试行程",
            "activities": []
        })
        mock_model.invoke.return_value = mock_response
        
        scene_service = SceneService(store, model=mock_model)
        itinerary_service = DailyItineraryService(store, model=mock_model, scene_service=scene_service)
        
        now = datetime.now(tz)
        
        # 第一次生成
        result1 = itinerary_service.ensure_for_day(now=now)
        itinerary_id_1 = result1["id"]
        
        # 第二次调用，应该返回相同的行程
        result2 = itinerary_service.ensure_for_day(now=now)
        itinerary_id_2 = result2["id"]
        
        assert itinerary_id_1 == itinerary_id_2
        assert result2["status"] == "generated"
        
        print("✅ 每日行程幂等性测试通过")


def test_scene_scheduler_run():
    """测试场景调度器基本运行。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        store.save_character("default", {
            "name": "林依"
        })
        
        mock_model = Mock()
        scene_service = SceneService(store, model=mock_model)
        itinerary_service = DailyItineraryService(store, model=mock_model, scene_service=scene_service)
        decision_service = ScheduleDecisionService(store, model=mock_model)
        
        scheduler = SceneScheduler(
            store,
            model=mock_model,
            itinerary=itinerary_service,
            scenes=scene_service,
            decisions=decision_service
        )
        
        tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        
        # 运行一次调度（不生成行程）
        actions = scheduler.run_once(now=now, generate=False)
        
        assert isinstance(actions, list)
        
        # 验证初始环境已创建
        current = scene_service.current()
        assert current is not None
        
        print("✅ 场景调度器运行测试通过")


def test_three_schedule_categories():
    """测试三类日程的区分。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        tz = ZoneInfo("Asia/Shanghai")
        tomorrow = datetime.now(tz) + timedelta(days=1)
        
        # Agent 个人日程
        store.create_schedule("agent_schedule_1", {
            "title": "Agent 个人学习",
            "due_at": tomorrow.isoformat(),
            "category": "agent",
            "owner": "agent",
            "participants": ["agent"]
        }, actor="agent")
        
        # 用户个人日程
        store.create_schedule("user_schedule_1", {
            "title": "用户个人会议",
            "due_at": tomorrow.isoformat(),
            "category": "user",
            "owner": "user",
            "participants": ["user"]
        }, actor="user")
        
        # 共同活动日程
        store.create_schedule("shared_schedule_1", {
            "title": "一起看电影",
            "due_at": tomorrow.isoformat(),
            "category": "shared",
            "owner": "agent",
            "participants": ["agent", "user"]
        }, actor="agent")
        
        # 验证三类日程都已创建
        agent_schedules = [s for s in store.schedules() if s.get("category") == "agent"]
        user_schedules = [s for s in store.schedules() if s.get("category") == "user"]
        shared_schedules = [s for s in store.schedules() if s.get("category") == "shared"]
        
        assert len(agent_schedules) >= 1
        assert len(user_schedules) >= 1
        assert len(shared_schedules) >= 1
        
        print("✅ 三类日程区分测试通过")


if __name__ == "__main__":
    print("🧪 开始日程驱动场景生成测试（Phase 3）...\n")
    
    try:
        test_initial_environment_idempotent()
        test_scene_hierarchy()
        test_current_scene_context()
        test_scene_pool_matching()
        test_daily_itinerary_structure()
        test_itinerary_idempotent()
        test_scene_scheduler_run()
        test_three_schedule_categories()
        
        print("\n" + "="*60)
        print("✅ 所有 Phase 3 核心测试通过！")
        print("   - 初始环境幂等创建 ✓")
        print("   - 场景层级结构 ✓")
        print("   - 场景上下文生成 ✓")
        print("   - 场景池匹配 ✓")
        print("   - 每日行程结构 ✓")
        print("   - 行程幂等性 ✓")
        print("   - 场景调度器 ✓")
        print("   - 三类日程区分 ✓")
        print("="*60)
        print("\n📋 Phase 3 核心验证：")
        print("   ✓ 初始化环境只创建一次")
        print("   ✓ 地点 → 区域 → 物体层级")
        print("   ✓ 场景池匹配与复用")
        print("   ✓ 每日行程生成与幂等")
        print("   ✓ 场景调度基础功能")
        print("   ✓ Agent/用户/共同日程分离")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"\n💥 测试错误: {e}")
        import traceback
        traceback.print_exc()
        raise
