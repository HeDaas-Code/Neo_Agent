#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI结构验证脚本 / GUI Structure Validation Script
用于验证GUI优化后的结构是否正确

This script validates the GUI structure after optimization.
"""

import ast
import sys
from pathlib import Path

def validate_gui_structure():
    """验证GUI结构"""
    gui_file = Path(__file__).parent / 'src' / 'gui' / 'gui_enhanced.py'
    
    if not gui_file.exists():
        print(f"❌ GUI文件不存在: {gui_file}")
        return False
    
    print(f"✓ GUI文件存在: {gui_file}")
    
    # 读取文件内容
    with open(gui_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键方法是否存在
    required_methods = [
        'create_widgets',
        'create_chat_page',
        'create_debug_page',
        'create_chat_area',
        'create_debug_area',
    ]
    
    print("\n检查关键方法 / Checking Key Methods:")
    all_methods_exist = True
    for method in required_methods:
        if f'def {method}(' in content:
            print(f"  ✓ {method}")
        else:
            print(f"  ❌ {method} 缺失")
            all_methods_exist = False
    
    # 检查主Notebook是否创建
    print("\n检查主要组件 / Checking Main Components:")
    
    checks = {
        'self.main_notebook = ttk.Notebook': '主Notebook创建',
        'text="💬 对话"': '对话标签页',
        'text="🔧 调试"': '调试标签页',
        'self.create_chat_page(chat_page)': '对话页面创建调用',
        'self.create_debug_page(debug_page)': '调试页面创建调用',
    }
    
    all_components_exist = True
    for pattern, description in checks.items():
        if pattern in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ❌ {description} 缺失")
            all_components_exist = False
    
    # 检查滚动条支持
    print("\n检查滚动条支持 / Checking Scrollbar Support:")
    scrollbar_components = [
        ('scrolledtext.ScrolledText', '对话显示区域'),
        ('self.chat_display = scrolledtext.ScrolledText', '聊天显示'),
        ('self.info_display = scrolledtext.ScrolledText', '系统信息'),
        ('self.short_term_display = scrolledtext.ScrolledText', '短期记忆'),
        ('self.long_term_display = scrolledtext.ScrolledText', '长期记忆'),
    ]
    
    for pattern, description in scrollbar_components:
        if pattern in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ⚠ {description} - 需要检查")
    
    # 检查调试标签页
    print("\n检查调试标签页 / Checking Debug Tabs:")
    debug_tabs = [
        ('text="系统信息"', '系统信息'),
        ('text="短期记忆"', '短期记忆'),
        ('text="长期记忆"', '长期记忆'),
        ('text="🧠 理解阶段"', '理解阶段'),
        ('text="📚 知识库"', '知识库'),
        ('text="👁️ 环境管理"', '环境管理'),
        ('text="💾 数据库管理"', '数据库管理'),
        ('text="📦 设定迁移"', '设定迁移'),
        ('text="⚙️ 控制面板"', '控制面板'),
        ('text="📅 日程管理"', '日程管理'),
        ('text="📋 事件管理"', '事件管理'),
        ('text="🔧 NPS工具"', 'NPS工具'),
    ]
    
    tabs_found = 0
    for pattern, description in debug_tabs:
        if pattern in content:
            print(f"  ✓ {description}")
            tabs_found += 1
        else:
            print(f"  ❌ {description} 缺失")
    
    print(f"\n找到 {tabs_found}/{len(debug_tabs)} 个调试标签页")
    
    # 总结
    print("\n" + "="*60)
    if all_methods_exist and all_components_exist and tabs_found >= 10:
        print("✅ GUI结构验证通过！")
        print("✅ GUI Structure Validation Passed!")
        return True
    else:
        print("❌ GUI结构验证失败，请检查以上问题")
        print("❌ GUI Structure Validation Failed, please check issues above")
        return False

if __name__ == '__main__':
    success = validate_gui_structure()
    sys.exit(0 if success else 1)
