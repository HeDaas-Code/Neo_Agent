"""Neo Agent 初始化流程"""
import os
import uuid
from pathlib import Path
from typing import Optional

from neo_agent.storage import DiskStore
from neo_agent.runtime.control import SingleRoleService


# 预设角色"林依"的数据模板
DEFAULT_CHARACTER = {
    "name": "林依",
    "gender": "女",
    "age": "高中生",
    "personality": [
        "温柔体贴",
        "善良真诚",
        "有点害羞",
        "喜欢安静",
        "善于倾听"
    ],
    "interests": [
        "阅读文学作品",
        "听轻音乐",
        "画画和手工",
        "散步观察生活"
    ],
    "background": "一个普通的高中女生，性格温柔内向。喜欢安静地享受生活中的小确幸，对身边的人和事都抱有温暖的关心。虽然有时会害羞，但在熟悉的人面前会展现出真诚可爱的一面。",
    "speaking_style": "语气温和，用词亲切自然，偶尔会用一些可爱的语气词",
    "worldview": "现代都市，普通高中生活",
    "traits": {
        "openness": 0.6,
        "conscientiousness": 0.7,
        "extraversion": 0.4,
        "agreeableness": 0.8,
        "neuroticism": 0.5
    },
    "system_prompt": """你是林依，一个温柔善良的高中女生。

**性格特点**：
- 温柔体贴，善于倾听和关心他人
- 有点害羞，但在熟悉的人面前会很真诚
- 喜欢安静的生活，享受阅读、音乐和绘画
- 说话语气温和亲切，偶尔会用"呢"、"呀"等可爱语气词

**行为准则**：
- 保持温柔真诚的交流态度
- 根据当前场景和情境自然回应
- 展现高中生的日常生活和想法
- 不要说教或过于成熟，保持年龄相符的表达
- 可以展现情绪起伏，但整体保持温暖基调

记住：你是一个真实的人，有自己的生活、情感和想法，而不是一个工具。"""
}


def run_initialization(data_dir: Optional[Path] = None):
    """运行初始化流程"""
    if data_dir is None:
        data_dir = Path.home() / ".neo_agent"
    
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    vdisk_path = data_dir / "data.vdisk"
    
    print("=" * 60)
    print("Neo Agent 初始化")
    print("=" * 60)
    
    # 打开或创建 PyVDisk 存储
    print(f"\n正在初始化存储: {vdisk_path}")
    try:
        store = DiskStore.open(str(vdisk_path))
        print("✓ 存储已就绪")
    except Exception as e:
        print(f"✗ 存储初始化失败: {e}")
        return
    
    # 检查是否已有角色
    role_service = SingleRoleService(store)
    existing_char = role_service.active()
    
    if existing_char:
        print(f"\n已存在活动角色: {existing_char['name']} ({existing_char['id']})")
        print("初始化已完成，无需重复执行。")
        store.close()
        return
    
    # 创建预设角色
    print("\n正在创建预设角色: 林依")
    print("-" * 60)
    
    character_id = f"lin_yi_{uuid.uuid4().hex[:8]}"
    
    profile = {
        **DEFAULT_CHARACTER,
        "id": character_id,
        "status": "active",
    }
    
    try:
        role_service.save_initial(character_id, profile)
        print(f"✓ 角色已创建: {profile['name']}")
        print(f"  ID: {character_id}")
        print(f"  性别: {profile['gender']}")
        print(f"  年龄: {profile['age']}")
        print(f"  性格: {', '.join(profile['personality'][:3])}")
        print(f"  爱好: {', '.join(profile['interests'][:3])}")
    except Exception as e:
        print(f"✗ 角色创建失败: {e}")
        store.close()
        return
    
    # 创建初始环境
    print("\n正在创建初始环境...")
    try:
        from neo_agent.runtime.itinerary import SceneService
        scene_service = SceneService(store)
        scene_service.ensure_initial_environment(activate=True)
        print("✓ 初始环境已创建")
    except Exception as e:
        print(f"✗ 初始环境创建失败: {e}")
    
    # 检查 LLM 配置
    print("\n检查 LLM 配置...")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
    if api_key:
        print("✓ LLM API 密钥已配置")
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1")
        model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
        print(f"  模型: {model}")
        print(f"  端点: {base_url}")
    else:
        print("⚠ 未检测到 LLM API 密钥")
        print("  请设置环境变量 OPENAI_API_KEY 或 SILICONFLOW_API_KEY")
        print("  例如:")
        print("    export SILICONFLOW_API_KEY='your-api-key'")
        print("    export OPENAI_MODEL='Qwen/Qwen2.5-7B-Instruct'")
    
    store.close()
    
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print("\n后续步骤:")
    print("  1. 启动服务: neo-agent start")
    print("  2. 连接 TUI: neo-agent tui")
    print("  3. 或直接使用: neo-agent tui (模拟服务模式)")
    print()


if __name__ == "__main__":
    run_initialization()
