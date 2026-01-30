"""
设定迁移管理模块
实现智能体设定的导出和导入功能，支持 .env 配置和数据库数据的完整迁移
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from database_manager import DatabaseManager


class SettingsMigration:
    """
    设定迁移管理器
    负责智能体设定的导出和导入
    """
    
    # 支持的数据表类别
    DATA_CATEGORIES = {
        'base_knowledge': '基础知识',
        'entities': '实体知识库',
        'short_term_memory': '短期记忆',
        'long_term_memory': '长期记忆',
        'emotion_history': '情感分析历史',
        'environment_descriptions': '环境描述',
        'environment_objects': '环境物体',
        'environment_connections': '环境连接',
        'environment_domains': '环境域',
        'domain_environments': '域环境关联',
        'agent_expressions': '智能体表达',
        'user_expression_habits': '用户表达习惯',
        'vision_tool_logs': '视觉工具日志',
        'metadata': '元数据'
    }
    
    def __init__(self, db_manager: DatabaseManager = None, env_path: str = ".env"):
        """
        初始化设定迁移管理器
        
        Args:
            db_manager: 数据库管理器实例
            env_path: .env 文件路径
        """
        self.db_manager = db_manager or DatabaseManager()
        self.env_path = env_path
        
    def export_settings(self, 
                       export_path: str,
                       include_env: bool = True,
                       selected_categories: List[str] = None) -> Dict[str, Any]:
        """
        导出智能体设定
        
        Args:
            export_path: 导出文件路径（不含扩展名）
            include_env: 是否包含 .env 配置
            selected_categories: 选择要导出的数据类别，None 表示全部导出
            
        Returns:
            包含导出结果的字典
        """
        result = {
            'success': False,
            'message': '',
            'exported_file': '',
            'stats': {}
        }
        
        try:
            # 准备导出数据
            export_data = {
                'export_info': {
                    'version': '1.0',
                    'exported_at': datetime.now().isoformat(),
                    'agent_name': os.getenv('CHARACTER_NAME', '未知'),
                },
                'env_settings': {},
                'database_data': {}
            }
            
            # 1. 导出 .env 配置
            if include_env:
                env_settings = self._read_env_file()
                export_data['env_settings'] = env_settings
                result['stats']['env_settings'] = len(env_settings)
            
            # 2. 导出数据库数据
            if selected_categories is None:
                selected_categories = list(self.DATA_CATEGORIES.keys())
            
            for category in selected_categories:
                if category in self.DATA_CATEGORIES:
                    data = self._export_category_data(category)
                    if data is not None:
                        export_data['database_data'][category] = data
                        result['stats'][category] = len(data) if isinstance(data, list) else 1
            
            # 3. 保存到文件
            export_file = f"{export_path}.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            result['success'] = True
            result['message'] = '导出成功'
            result['exported_file'] = export_file
            
        except Exception as e:
            result['message'] = f'导出失败: {str(e)}'
            
        return result
    
    def import_settings(self,
                       import_path: str,
                       import_env: bool = True,
                       import_database: bool = True,
                       overwrite: bool = False,
                       selected_categories: List[str] = None) -> Dict[str, Any]:
        """
        导入智能体设定
        
        Args:
            import_path: 导入文件路径
            import_env: 是否导入 .env 配置
            import_database: 是否导入数据库数据
            overwrite: 是否覆盖现有数据
            selected_categories: 选择要导入的数据类别，None 表示全部导入
            
        Returns:
            包含导入结果的字典
        """
        result = {
            'success': False,
            'message': '',
            'stats': {}
        }
        
        # 验证文件是否存在
        if not os.path.exists(import_path):
            result['message'] = f'文件不存在: {import_path}'
            return result
        
        try:
            # 1. 读取导入文件
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 2. 导入 .env 配置
            if import_env and 'env_settings' in import_data:
                # 备份当前 .env
                if os.path.exists(self.env_path):
                    backup_path = f"{self.env_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.env_path, backup_path)
                    result['backup_env'] = backup_path
                
                # 写入新配置
                self._write_env_file(import_data['env_settings'], overwrite)
                result['stats']['env_settings'] = len(import_data['env_settings'])
            
            # 3. 导入数据库数据
            if import_database and 'database_data' in import_data:
                db_data = import_data['database_data']
                
                if selected_categories is None:
                    selected_categories = list(db_data.keys())
                
                for category in selected_categories:
                    if category in db_data:
                        count = self._import_category_data(category, db_data[category], overwrite)
                        result['stats'][category] = count
            
            result['success'] = True
            result['message'] = '导入成功'
            
        except json.JSONDecodeError as e:
            result['message'] = f'JSON格式错误: {str(e)}'
        except FileNotFoundError as e:
            result['message'] = f'文件未找到: {str(e)}'
        except PermissionError as e:
            result['message'] = f'文件权限不足: {str(e)}'
        except shutil.Error as e:
            result['message'] = f'备份文件失败: {str(e)}'
        except Exception as e:
            result['message'] = f'导入失败: {str(e)}'
            
        return result
    
    def preview_import(self, import_path: str) -> Dict[str, Any]:
        """
        预览导入文件内容
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            包含预览信息的字典
        """
        preview = {
            'success': False,
            'message': '',
            'export_info': {},
            'categories': {},
            'env_settings_count': 0
        }
        
        # 验证文件是否存在
        if not os.path.exists(import_path):
            preview['message'] = f'文件不存在: {import_path}'
            return preview
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            preview['export_info'] = import_data.get('export_info', {})
            
            # 统计环境变量
            if 'env_settings' in import_data:
                preview['env_settings_count'] = len(import_data['env_settings'])
            
            # 统计各类别数据
            if 'database_data' in import_data:
                for category, data in import_data['database_data'].items():
                    if category in self.DATA_CATEGORIES:
                        preview['categories'][category] = {
                            'name': self.DATA_CATEGORIES[category],
                            'count': len(data) if isinstance(data, list) else 1
                        }
            
            preview['success'] = True
            
        except json.JSONDecodeError as e:
            preview['message'] = f'JSON格式错误: {str(e)}'
        except FileNotFoundError as e:
            preview['message'] = f'文件未找到: {str(e)}'
        except PermissionError as e:
            preview['message'] = f'文件权限不足: {str(e)}'
        except Exception as e:
            preview['message'] = f'预览失败: {str(e)}'
            
        return preview
    
    def _read_env_file(self) -> Dict[str, str]:
        """
        读取 .env 文件内容
        
        Returns:
            环境变量字典
        """
        env_settings = {}
        
        if not os.path.exists(self.env_path):
            return env_settings
        
        with open(self.env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_settings[key.strip()] = value.strip()
        
        return env_settings
    
    def _write_env_file(self, env_settings: Dict[str, str], overwrite: bool = False):
        """
        写入 .env 文件
        
        Args:
            env_settings: 环境变量字典
            overwrite: 是否覆盖现有配置
        """
        # 如果不覆盖，先读取现有配置
        existing_settings = {}
        if not overwrite and os.path.exists(self.env_path):
            existing_settings = self._read_env_file()
        
        # 合并配置（新配置优先）
        if not overwrite:
            env_settings = {**existing_settings, **env_settings}
        
        # 写入文件
        with open(self.env_path, 'w', encoding='utf-8') as f:
            f.write("# Neo Agent 配置文件\n")
            f.write(f"# 导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 按类别分组写入
            api_keys = ['SILICONFLOW_API_KEY', 'SILICONFLOW_API_URL']
            model_keys = ['MODEL_NAME', 'TEMPERATURE', 'MAX_TOKENS']
            character_keys = [k for k in env_settings.keys() if k.startswith('CHARACTER_')]
            memory_keys = [k for k in env_settings.keys() if 'MEMORY' in k]
            
            # API配置
            f.write("# API配置\n")
            for key in api_keys:
                if key in env_settings:
                    f.write(f"{key}={env_settings[key]}\n")
            f.write("\n")
            
            # 模型配置
            f.write("# LLM模型配置\n")
            for key in model_keys:
                if key in env_settings:
                    f.write(f"{key}={env_settings[key]}\n")
            f.write("\n")
            
            # 角色设定
            f.write("# 角色设定\n")
            for key in character_keys:
                if key in env_settings:
                    f.write(f"{key}={env_settings[key]}\n")
            f.write("\n")
            
            # 记忆设置
            f.write("# 记忆设置\n")
            for key in memory_keys:
                if key in env_settings:
                    f.write(f"{key}={env_settings[key]}\n")
            f.write("\n")
            
            # 其他配置
            other_keys = [k for k in env_settings.keys() 
                         if k not in api_keys + model_keys + character_keys + memory_keys]
            if other_keys:
                f.write("# 其他配置\n")
                for key in other_keys:
                    f.write(f"{key}={env_settings[key]}\n")
    
    def _export_category_data(self, category: str) -> Optional[List[Dict] | Dict]:
        """
        导出指定类别的数据
        
        Args:
            category: 数据类别
            
        Returns:
            数据列表或字典
        """
        # 验证类别是否合法
        if category not in self.DATA_CATEGORIES:
            print(f"✗ 无效的数据类别: {category}")
            return None
            
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 使用参数化查询防止SQL注入（表名通过验证）
                # SQLite不支持表名参数化，但我们已经验证了category在白名单中
                cursor.execute(f"SELECT * FROM {category}")
                rows = cursor.fetchall()
                
                # 转换为字典列表
                data = []
                for row in rows:
                    data.append(dict(row))
                
                return data
                
        except Exception as e:
            print(f"✗ 导出 {category} 数据时出错: {e}")
            return None
    
    def _import_category_data(self, category: str, data: List[Dict], overwrite: bool = False) -> int:
        """
        导入指定类别的数据
        
        Args:
            category: 数据类别
            data: 数据列表
            overwrite: 是否覆盖现有数据
            
        Returns:
            导入的记录数
        """
        # 验证类别是否合法
        if category not in self.DATA_CATEGORIES:
            print(f"✗ 无效的数据类别: {category}")
            return 0
            
        count = 0
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 如果覆盖，先清空表
                if overwrite:
                    cursor.execute(f"DELETE FROM {category}")
                
                # 插入数据
                for item in data:
                    if not item:
                        continue
                    
                    # 验证所有列名（防止SQL注入）
                    columns = list(item.keys())
                    # 只允许常见的列名字符
                    for col in columns:
                        if not col.replace('_', '').isalnum():
                            print(f"✗ 无效的列名: {col}")
                            continue
                    
                    # 构建 INSERT 语句
                    placeholders = ','.join(['?' for _ in columns])
                    column_names = ','.join(columns)
                    values = [item[col] for col in columns]
                    
                    try:
                        if overwrite:
                            cursor.execute(
                                f"INSERT INTO {category} ({column_names}) VALUES ({placeholders})",
                                values
                            )
                            if cursor.rowcount > 0:
                                count += 1
                        else:
                            cursor.execute(
                                f"INSERT OR IGNORE INTO {category} ({column_names}) VALUES ({placeholders})",
                                values
                            )
                            if cursor.rowcount > 0:
                                count += 1
                    except Exception as e:
                        print(f"✗ 导入记录时出错: {e}")
                        continue
                
        except Exception as e:
            print(f"✗ 导入 {category} 数据时出错: {e}")
            
        return count
    
    def get_available_categories(self) -> Dict[str, str]:
        """
        获取可用的数据类别
        
        Returns:
            类别字典 {类别键: 类别名称}
        """
        return self.DATA_CATEGORIES.copy()
