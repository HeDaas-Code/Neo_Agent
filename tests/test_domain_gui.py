"""
测试域和环境管理GUI功能
"""
import pytest

tk = pytest.importorskip("tkinter")

from src.core.database_manager import DatabaseManager
from src.gui.database_gui import DatabaseManagerGUI


def test_domain_gui():
    """测试域和环境GUI"""
    print("=" * 60)
    print("域和环境管理GUI测试")
    print("=" * 60)
    
    # 初始化数据库
    db = DatabaseManager("test_domain_gui.db", debug=False)
    
    # 创建一些测试数据
    print("\n创建测试数据...")
    
    # 创建环境
    room_uuid = db.create_environment(
        name="测试房间",
        overall_description="这是一个测试房间",
        atmosphere="测试氛围",
        lighting="测试光照"
    )
    print(f"✓ 创建环境: 测试房间")
    
    living_room_uuid = db.create_environment(
        name="测试客厅",
        overall_description="这是一个测试客厅",
        atmosphere="温馨",
        lighting="明亮"
    )
    print(f"✓ 创建环境: 测试客厅")
    
    # 创建域
    home_domain_uuid = db.create_domain(
        name="测试家",
        description="测试用的家",
        default_environment_uuid=living_room_uuid
    )
    print(f"✓ 创建域: 测试家")
    
    # 添加环境到域
    db.add_environment_to_domain(home_domain_uuid, room_uuid)
    db.add_environment_to_domain(home_domain_uuid, living_room_uuid)
    print(f"✓ 添加环境到域")
    
    print("\n启动GUI测试...")
    print("请检查以下功能:")
    print("1. 🗺️ 环境管理标签页是否存在")
    print("2. 🏘️ 域管理标签页是否存在")
    print("3. 环境列表是否正确显示")
    print("4. 域列表是否正确显示")
    print("5. 各个按钮是否可用")
    print("\n关闭窗口后测试数据将被删除")
    
    # 创建GUI
    root = tk.Tk()
    root.title("域和环境管理GUI测试")
    root.geometry("1000x700")
    
    # 创建数据库管理GUI
    gui = DatabaseManagerGUI(root, db)
    
    # 切换到环境管理标签页
    try:
        gui.notebook.select(5)  # 环境管理是第6个标签页（索引5）
    except:
        print("注意: 无法自动切换到环境管理标签页")
    
    root.mainloop()
    
    # 清理测试数据
    import os
    if os.path.exists("test_domain_gui.db"):
        os.remove("test_domain_gui.db")
        print("\n✓ 测试数据已清理")
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_domain_gui()
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
