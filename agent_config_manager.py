"""
智能体配置管理模块
用于导出和导入智能体的完整配置，包括环境变量、环境描述和基础记忆
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from database_manager import DatabaseManager


class AgentConfigManager:
    """
    智能体配置管理器
    负责导出和导入智能体的完整配置
    """
    
    def __init__(self, db_manager: DatabaseManager = None, env_file: str = ".env"):
        """
        初始化配置管理器
        
        Args:
            db_manager: 数据库管理器实例
            env_file: 环境变量文件路径
        """
        self.db = db_manager or DatabaseManager()
        self.env_file = env_file
    
    def export_config(self, output_file: str) -> bool:
        """
        导出智能体配置到JSON文件
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            print("○ 开始导出智能体配置...")
            
            # 1. 读取.env配置
            env_config = self._read_env_config()
            
            # 2. 导出环境描述
            environments = self._export_environments()
            
            # 3. 导出基础知识
            base_knowledge = self._export_base_knowledge()
            
            # 4. 导出智能体表达风格
            agent_expressions = self._export_agent_expressions()
            
            # 5. 导出环境域
            domains = self._export_domains()
            
            # 6. 组装完整配置
            config_data = {
                "version": "1.0",
                "export_time": datetime.now().isoformat(),
                "env_config": env_config,
                "environments": environments,
                "domains": domains,
                "base_knowledge": base_knowledge,
                "agent_expressions": agent_expressions
            }
            
            # 6. 写入JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 配置导出成功: {output_file}")
            print(f"  - 环境变量: {len(env_config)} 项")
            print(f"  - 环境描述: {len(environments)} 个")
            print(f"  - 环境域: {len(domains)} 个")
            print(f"  - 基础知识: {len(base_knowledge)} 条")
            print(f"  - 表达风格: {len(agent_expressions)} 个")
            return True
            
        except Exception as e:
            print(f"✗ 导出配置时出错: {e}")
            return False
    
    def import_config(self, input_file: str, overwrite: bool = False) -> bool:
        """
        从JSON文件导入智能体配置
        
        Args:
            input_file: 输入文件路径
            overwrite: 是否覆盖现有配置（默认False）
            
        Returns:
            是否导入成功
        """
        try:
            print("○ 开始导入智能体配置...")
            
            # 1. 读取JSON文件
            if not os.path.exists(input_file):
                print(f"✗ 配置文件不存在: {input_file}")
                return False
            
            with open(input_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 2. 验证配置格式
            if not self._validate_config(config_data):
                print("✗ 配置文件格式无效")
                return False
            
            print(f"✓ 配置文件验证通过 (版本: {config_data.get('version', 'unknown')})")
            
            # 3. 导入环境变量
            env_count = self._import_env_config(config_data.get('env_config', {}), overwrite)
            
            # 4. 导入环境描述
            env_desc_count = self._import_environments(config_data.get('environments', []), overwrite)
            
            # 5. 导入环境域
            domain_count = self._import_domains(config_data.get('domains', []), overwrite)
            
            # 6. 导入基础知识
            knowledge_count = self._import_base_knowledge(config_data.get('base_knowledge', []), overwrite)
            
            # 7. 导入智能体表达风格
            expr_count = self._import_agent_expressions(config_data.get('agent_expressions', []), overwrite)
            
            print(f"✓ 配置导入完成:")
            print(f"  - 环境变量: {env_count} 项")
            print(f"  - 环境描述: {env_desc_count} 个")
            print(f"  - 环境域: {domain_count} 个")
            print(f"  - 基础知识: {knowledge_count} 条")
            print(f"  - 表达风格: {expr_count} 个")
            return True
            
        except Exception as e:
            print(f"✗ 导入配置时出错: {e}")
            return False
    
    def _read_env_config(self) -> Dict[str, str]:
        """
        读取.env文件配置
        
        Returns:
            环境变量配置字典
        """
        env_config = {}
        
        if not os.path.exists(self.env_file):
            print(f"⚠ 环境变量文件不存在: {self.env_file}")
            return env_config
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_config[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠ 读取环境变量文件时出错: {e}")
        
        return env_config
    
    def _export_environments(self) -> List[Dict[str, Any]]:
        """
        导出所有环境描述
        
        Returns:
            环境描述列表
        """
        environments = []
        
        try:
            # 获取所有环境
            all_envs = self.db.get_all_environments()
            
            for env in all_envs:
                # 获取环境中的物体
                objects = self.db.get_environment_objects(env['uuid'], visible_only=False)
                
                # 获取环境连接
                connections = self.db.get_environment_connections(env['uuid'])
                
                env_data = {
                    'name': env['name'],
                    'overall_description': env['overall_description'],
                    'atmosphere': env.get('atmosphere', ''),
                    'lighting': env.get('lighting', ''),
                    'sounds': env.get('sounds', ''),
                    'smells': env.get('smells', ''),
                    'is_active': env.get('is_active', 0),
                    'objects': [
                        {
                            'name': obj['name'],
                            'description': obj['description'],
                            'position': obj.get('position', ''),
                            'properties': obj.get('properties', ''),
                            'interaction_hints': obj.get('interaction_hints', ''),
                            'priority': obj.get('priority', 50),
                            'is_visible': obj.get('is_visible', 1)
                        }
                        for obj in objects
                    ],
                    'connections': [
                        {
                            'to_environment_name': self._get_env_name_by_uuid(conn['to_environment_uuid']),
                            'connection_type': conn.get('connection_type', 'normal'),
                            'direction': conn.get('direction', 'bidirectional'),
                            'description': conn.get('description', '')
                        }
                        for conn in connections if conn['from_environment_uuid'] == env['uuid']
                    ]
                }
                
                environments.append(env_data)
        
        except Exception as e:
            print(f"⚠ 导出环境描述时出错: {e}")
        
        return environments
    
    def _export_base_knowledge(self) -> List[Dict[str, Any]]:
        """
        导出所有基础知识
        
        Returns:
            基础知识列表
        """
        base_knowledge = []
        
        try:
            all_facts = self.db.get_all_base_facts()
            
            for fact in all_facts:
                knowledge_data = {
                    'entity_name': fact['entity_name'],
                    'content': fact['content'],
                    'category': fact.get('category', '通用'),
                    'description': fact.get('description', ''),
                    'immutable': bool(fact.get('immutable', 1)),
                    'priority': fact.get('priority', 100),
                    'confidence': fact.get('confidence', 1.0)
                }
                base_knowledge.append(knowledge_data)
        
        except Exception as e:
            print(f"⚠ 导出基础知识时出错: {e}")
        
        return base_knowledge
    
    def _export_agent_expressions(self) -> List[Dict[str, Any]]:
        """
        导出智能体表达风格
        
        Returns:
            表达风格列表
        """
        expressions = []
        
        try:
            all_expressions = self.db.get_all_agent_expressions(active_only=False)
            
            for expr in all_expressions:
                expr_data = {
                    'expression': expr['expression'],
                    'meaning': expr['meaning'],
                    'category': expr.get('category', '通用'),
                    'is_active': bool(expr.get('is_active', 1))
                }
                expressions.append(expr_data)
        
        except Exception as e:
            print(f"⚠ 导出表达风格时出错: {e}")
        
        return expressions
    
    def _export_domains(self) -> List[Dict[str, Any]]:
        """
        导出所有环境域
        
        Returns:
            域列表
        """
        domains = []
        
        try:
            # 获取所有域
            all_domains = self.db.get_all_domains()
            
            for domain in all_domains:
                # 获取域中的环境
                domain_envs = self.db.get_domain_environments(domain['uuid'])
                
                # 获取默认环境名称
                default_env_name = ''
                if domain.get('default_environment_uuid'):
                    default_env_name = self._get_env_name_by_uuid(domain['default_environment_uuid'])
                
                domain_data = {
                    'name': domain['name'],
                    'description': domain.get('description', ''),
                    'default_environment_name': default_env_name,
                    'environment_names': [env['name'] for env in domain_envs]
                }
                
                domains.append(domain_data)
        
        except Exception as e:
            print(f"⚠ 导出环境域时出错: {e}")
        
        return domains
    
    def _get_env_name_by_uuid(self, env_uuid: str) -> str:
        """
        根据UUID获取环境名称
        
        Args:
            env_uuid: 环境UUID
            
        Returns:
            环境名称
        """
        try:
            env = self.db.get_environment(env_uuid)
            if env:
                return env['name']
        except:
            pass
        return ''
    
    def _validate_config(self, config_data: Dict[str, Any]) -> bool:
        """
        验证配置文件格式
        
        Args:
            config_data: 配置数据
            
        Returns:
            是否有效
        """
        required_keys = ['version', 'env_config', 'environments', 'base_knowledge']
        for key in required_keys:
            if key not in config_data:
                print(f"✗ 配置文件缺少必需字段: {key}")
                return False
        return True
    
    def _import_env_config(self, env_config: Dict[str, str], overwrite: bool) -> int:
        """
        导入环境变量配置
        
        Args:
            env_config: 环境变量配置
            overwrite: 是否覆盖现有配置
            
        Returns:
            导入的配置项数量
        """
        if not env_config:
            return 0
        
        count = 0
        output_file = self.env_file if overwrite else f"{self.env_file}.new"
        
        try:
            # 如果是覆盖模式，读取现有注释
            existing_comments = []
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('#') or not line.strip():
                            existing_comments.append(line)
            
            # 写入新配置
            with open(output_file, 'w', encoding='utf-8') as f:
                # 保留原有注释
                if existing_comments:
                    f.writelines(existing_comments)
                    if existing_comments[-1].strip():  # 如果最后一行不是空行，添加一个空行
                        f.write('\n')
                
                # 写入配置
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
                    count += 1
            
            if not overwrite:
                print(f"  ⚠ 环境变量已保存到新文件: {output_file}")
                print(f"  请手动检查并重命名为 {self.env_file}")
        
        except Exception as e:
            print(f"⚠ 导入环境变量时出错: {e}")
        
        return count
    
    def _import_environments(self, environments: List[Dict[str, Any]], overwrite: bool) -> int:
        """
        导入环境描述
        
        Args:
            environments: 环境描述列表
            overwrite: 是否覆盖现有数据
            
        Returns:
            导入的环境数量
        """
        if not environments:
            return 0
        
        count = 0
        env_name_to_uuid = {}  # 用于存储环境名称到UUID的映射
        
        try:
            for env_data in environments:
                env_name = env_data.get('name', '')
                if not env_name:
                    continue
                
                # 检查是否已存在
                existing_envs = self.db.get_all_environments()
                existing_env = next((e for e in existing_envs if e['name'] == env_name), None)
                
                if existing_env and not overwrite:
                    print(f"  ⚠ 环境已存在，跳过: {env_name}")
                    env_name_to_uuid[env_name] = existing_env['uuid']
                    continue
                
                # 创建或更新环境
                if existing_env and overwrite:
                    # 更新现有环境
                    self.db.update_environment(
                        existing_env['uuid'],
                        overall_description=env_data.get('overall_description', ''),
                        atmosphere=env_data.get('atmosphere', ''),
                        lighting=env_data.get('lighting', ''),
                        sounds=env_data.get('sounds', ''),
                        smells=env_data.get('smells', ''),
                        is_active=env_data.get('is_active', 0)
                    )
                    env_uuid = existing_env['uuid']
                    
                    # 删除旧物体
                    old_objects = self.db.get_environment_objects(env_uuid, visible_only=False)
                    for obj in old_objects:
                        self.db.delete_object(obj['uuid'])
                else:
                    # 创建新环境
                    env_uuid = self.db.create_environment(
                        name=env_name,
                        overall_description=env_data.get('overall_description', ''),
                        atmosphere=env_data.get('atmosphere', ''),
                        lighting=env_data.get('lighting', ''),
                        sounds=env_data.get('sounds', ''),
                        smells=env_data.get('smells', '')
                    )
                    
                    # 设置激活状态
                    if env_data.get('is_active', 0):
                        self.db.set_active_environment(env_uuid)
                
                env_name_to_uuid[env_name] = env_uuid
                
                # 添加物体
                for obj_data in env_data.get('objects', []):
                    self.db.add_environment_object(
                        environment_uuid=env_uuid,
                        name=obj_data.get('name', ''),
                        description=obj_data.get('description', ''),
                        position=obj_data.get('position', ''),
                        properties=obj_data.get('properties', ''),
                        interaction_hints=obj_data.get('interaction_hints', ''),
                        priority=obj_data.get('priority', 50)
                    )
                    # 设置可见性
                    if not obj_data.get('is_visible', 1):
                        # 获取刚创建的物体并设置为不可见
                        objects = self.db.get_environment_objects(env_uuid, visible_only=False)
                        if objects:
                            self.db.update_object(objects[-1]['uuid'], is_visible=0)
                
                count += 1
            
            # 在第二遍中创建连接（因为需要所有环境都已创建）
            for env_data in environments:
                env_name = env_data.get('name', '')
                if env_name not in env_name_to_uuid:
                    continue
                
                from_uuid = env_name_to_uuid[env_name]
                
                for conn_data in env_data.get('connections', []):
                    to_name = conn_data.get('to_environment_name', '')
                    if to_name and to_name in env_name_to_uuid:
                        to_uuid = env_name_to_uuid[to_name]
                        try:
                            # 检查连接是否已存在
                            existing_conns = self.db.get_environment_connections(from_uuid)
                            conn_exists = any(
                                c['to_environment_uuid'] == to_uuid 
                                for c in existing_conns
                            )
                            
                            if not conn_exists:
                                self.db.create_environment_connection(
                                    from_env_uuid=from_uuid,
                                    to_env_uuid=to_uuid,
                                    connection_type=conn_data.get('connection_type', 'normal'),
                                    direction=conn_data.get('direction', 'bidirectional'),
                                    description=conn_data.get('description', '')
                                )
                        except Exception as e:
                            # 忽略连接创建错误（可能是重复连接）
                            pass
        
        except Exception as e:
            print(f"⚠ 导入环境描述时出错: {e}")
        
        return count
    
    def _import_base_knowledge(self, base_knowledge: List[Dict[str, Any]], overwrite: bool) -> int:
        """
        导入基础知识
        
        Args:
            base_knowledge: 基础知识列表
            overwrite: 是否覆盖现有数据
            
        Returns:
            导入的知识数量
        """
        if not base_knowledge:
            return 0
        
        count = 0
        
        try:
            for knowledge_data in base_knowledge:
                entity_name = knowledge_data.get('entity_name', '')
                if not entity_name:
                    continue
                
                # 检查是否已存在
                existing = self.db.get_base_fact(entity_name)
                
                if existing and not overwrite:
                    print(f"  ⚠ 基础知识已存在，跳过: {entity_name}")
                    continue
                
                # 如果是覆盖模式且不可变，先删除旧的
                if existing and overwrite:
                    if existing.get('immutable'):
                        print(f"  ⚠ 基础知识不可变，无法覆盖: {entity_name}")
                        continue
                    self.db.delete_base_fact(entity_name)
                
                # 添加新的基础知识
                self.db.add_base_fact(
                    entity_name=entity_name,
                    content=knowledge_data.get('content', ''),
                    category=knowledge_data.get('category', '通用'),
                    description=knowledge_data.get('description', ''),
                    immutable=knowledge_data.get('immutable', True)
                )
                
                count += 1
        
        except Exception as e:
            print(f"⚠ 导入基础知识时出错: {e}")
        
        return count
    
    def _import_agent_expressions(self, expressions: List[Dict[str, Any]], overwrite: bool) -> int:
        """
        导入智能体表达风格
        
        Args:
            expressions: 表达风格列表
            overwrite: 是否覆盖现有数据
            
        Returns:
            导入的表达数量
        """
        if not expressions:
            return 0
        
        count = 0
        
        try:
            for expr_data in expressions:
                expression = expr_data.get('expression', '')
                if not expression:
                    continue
                
                # 检查是否已存在（通过查询所有表达并比较）
                existing_exprs = self.db.get_all_agent_expressions(active_only=False)
                existing = next((e for e in existing_exprs if e['expression'] == expression), None)
                
                if existing and not overwrite:
                    print(f"  ⚠ 表达风格已存在，跳过: {expression}")
                    continue
                
                # 如果是覆盖模式，更新现有表达
                if existing and overwrite:
                    self.db.update_agent_expression(
                        existing['uuid'],
                        meaning=expr_data.get('meaning', ''),
                        category=expr_data.get('category', '通用'),
                        is_active=1 if expr_data.get('is_active', True) else 0
                    )
                else:
                    # 添加新表达
                    self.db.add_agent_expression(
                        expression=expression,
                        meaning=expr_data.get('meaning', ''),
                        category=expr_data.get('category', '通用')
                    )
                    # 设置激活状态
                    if not expr_data.get('is_active', True):
                        # 获取刚创建的表达并设置为不激活
                        all_exprs = self.db.get_all_agent_expressions(active_only=False)
                        if all_exprs:
                            self.db.update_agent_expression(all_exprs[-1]['uuid'], is_active=0)
                
                count += 1
        
        except Exception as e:
            print(f"⚠ 导入表达风格时出错: {e}")
        
        return count
    
    def _import_domains(self, domains: List[Dict[str, Any]], overwrite: bool) -> int:
        """
        导入环境域
        
        Args:
            domains: 域列表
            overwrite: 是否覆盖现有数据
            
        Returns:
            导入的域数量
        """
        if not domains:
            return 0
        
        count = 0
        
        try:
            # 先创建环境名称到UUID的映射
            all_envs = self.db.get_all_environments()
            env_name_to_uuid = {env['name']: env['uuid'] for env in all_envs}
            
            for domain_data in domains:
                domain_name = domain_data.get('name', '')
                if not domain_name:
                    continue
                
                # 检查是否已存在
                existing_domain = self.db.get_domain_by_name(domain_name)
                
                if existing_domain and not overwrite:
                    print(f"  ⚠ 环境域已存在，跳过: {domain_name}")
                    continue
                
                # 获取默认环境UUID
                default_env_uuid = None
                default_env_name = domain_data.get('default_environment_name', '')
                if default_env_name and default_env_name in env_name_to_uuid:
                    default_env_uuid = env_name_to_uuid[default_env_name]
                
                # 创建或更新域
                if existing_domain and overwrite:
                    # 更新现有域
                    self.db.update_domain(
                        existing_domain['uuid'],
                        description=domain_data.get('description', ''),
                        default_environment_uuid=default_env_uuid
                    )
                    domain_uuid = existing_domain['uuid']
                    
                    # 清空现有的环境关联
                    existing_envs = self.db.get_domain_environments(domain_uuid)
                    for env in existing_envs:
                        self.db.remove_environment_from_domain(domain_uuid, env['uuid'])
                else:
                    # 创建新域
                    domain_uuid = self.db.create_domain(
                        name=domain_name,
                        description=domain_data.get('description', ''),
                        default_environment_uuid=default_env_uuid
                    )
                
                # 添加环境到域
                env_names = domain_data.get('environment_names', [])
                for env_name in env_names:
                    if env_name in env_name_to_uuid:
                        env_uuid = env_name_to_uuid[env_name]
                        self.db.add_environment_to_domain(domain_uuid, env_uuid)
                
                count += 1
        
        except Exception as e:
            print(f"⚠ 导入环境域时出错: {e}")
        
        return count


if __name__ == '__main__':
    print("=" * 60)
    print("智能体配置管理器测试")
    print("=" * 60)
    
    # 创建配置管理器
    config_manager = AgentConfigManager()
    
    # 测试导出
    print("\n测试导出配置:")
    if config_manager.export_config("test_agent_config.json"):
        print("✓ 配置导出成功")
    
    # 测试导入
    print("\n测试导入配置:")
    if config_manager.import_config("test_agent_config.json", overwrite=False):
        print("✓ 配置导入成功")
    
    print("\n✓ 测试完成")
