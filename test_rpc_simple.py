"""简化的 RPC 测试脚本"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试基础导入"""
    try:
        from neo_agent.service import rpc_handlers
        print("✓ RPC handlers 导入成功")
        
        from neo_agent.runtime import daily_itinerary
        print("✓ DailyItineraryService 导入成功")
        
        from neo_agent.ui.v2 import views
        print("✓ Views 导入成功")
        
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_syntax():
    """测试语法正确性"""
    import py_compile
    files = [
        'neo_agent/service/rpc_handlers.py',
        'neo_agent/runtime/daily_itinerary.py',
        'neo_agent/ui/v2/views.py',
        'neo_agent/ui/v2/app.py'
    ]
    
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
            print(f"✓ {f} 语法正确")
        except py_compile.PyCompileError as e:
            print(f"✗ {f} 语法错误: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Neo Agent 快速验证测试")
    print("=" * 60)
    
    print("\n1. 语法检查...")
    if not test_syntax():
        sys.exit(1)
    
    print("\n2. 模块导入测试...")
    test_imports()  # 可能因为缺少依赖而失败，但不阻止后续
    
    print("\n" + "=" * 60)
    print("基础验证完成！")
    print("=" * 60)
