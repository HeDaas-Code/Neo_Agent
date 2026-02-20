"""
世界观构建系统
基于 Markdown 的智能体世界观构建模块，支持：
1. 直接编辑源文本的世界观管理
2. 自然语言世界观构建
3. 通过 Cognee 转化为模块化知识块
4. 与现有框架的知识库集成

用户可以通过自然语言描述来构建自己的虚拟世界观
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.tools.debug_logger import get_debug_logger
from src.core.prompt_manager import get_prompt_manager
from src.core.database_manager import DatabaseManager

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class WorldviewModule:
    """
    世界观模块数据类
    表示一个世界观的独立模块/知识块
    """
    
    def __init__(
        self,
        name: str,
        category: str,
        content: str,
        source_file: str = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化世界观模块
        
        Args:
            name: 模块名称
            category: 分类（general/rules/locations/characters/events/items）
            content: 模块内容
            source_file: 来源文件路径
            metadata: 附加元数据
        """
        self.name = name
        self.category = category
        self.content = content
        self.source_file = source_file
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category,
            "content": self.content,
            "source_file": self.source_file,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WorldviewModule':
        """从字典创建"""
        module = WorldviewModule(
            name=data["name"],
            category=data["category"],
            content=data["content"],
            source_file=data.get("source_file"),
            metadata=data.get("metadata", {})
        )
        module.created_at = data.get("created_at", module.created_at)
        module.updated_at = data.get("updated_at", module.updated_at)
        return module


class WorldviewBuilder:
    """
    世界观构建器
    
    提供基于 Markdown 的世界观管理和构建功能：
    1. 加载和解析 Markdown 世界观文件
    2. 自然语言转化为结构化世界观
    3. 模块化知识块管理
    4. 与 Cognee 和现有知识库集成
    """
    
    # 世界观分类
    CATEGORIES = {
        "general": "基本信息",
        "rules": "规则设定",
        "locations": "地点场所",
        "characters": "角色人物",
        "events": "事件历史",
        "items": "物品道具",
        "culture": "文化习俗",
        "technology": "科技水平"
    }
    
    def __init__(
        self,
        worldview_dir: str = None,
        db_manager: DatabaseManager = None,
        cognee_manager = None
    ):
        """
        初始化世界观构建器
        
        Args:
            worldview_dir: 世界观文件目录
            db_manager: 数据库管理器
            cognee_manager: Cognee 记忆管理器
        """
        # 设置世界观目录
        if worldview_dir is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            worldview_dir = project_root / "prompts" / "worldview"
        
        self.worldview_dir = Path(worldview_dir)
        self.db = db_manager or DatabaseManager()
        self.cognee_manager = cognee_manager
        self.prompt_manager = get_prompt_manager()
        
        # 模块缓存
        self._modules_cache: Dict[str, WorldviewModule] = {}
        
        # 确保目录存在
        self.worldview_dir.mkdir(parents=True, exist_ok=True)
        
        debug_logger.log_module('WorldviewBuilder', '世界观构建器初始化', {
            'worldview_dir': str(self.worldview_dir)
        })
        
        print(f"✓ 世界观构建系统已初始化 (目录: {self.worldview_dir})")
    
    def list_worldview_files(self) -> List[Dict[str, Any]]:
        """
        列出所有世界观文件
        
        Returns:
            世界观文件信息列表
        """
        files = []
        for md_file in self.worldview_dir.glob("*.md"):
            stat = md_file.stat()
            files.append({
                "name": md_file.stem,
                "path": str(md_file),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return sorted(files, key=lambda x: x["name"])
    
    def load_worldview(self, name: str) -> str:
        """
        加载世界观文件内容
        
        Args:
            name: 世界观名称（不含 .md 后缀）
            
        Returns:
            世界观内容
        """
        file_path = self.worldview_dir / f"{name}.md"
        
        if not file_path.exists():
            raise FileNotFoundError(f"世界观文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_worldview(self, name: str, content: str) -> bool:
        """
        保存世界观到文件
        
        Args:
            name: 世界观名称
            content: 世界观内容
            
        Returns:
            是否成功保存
        """
        try:
            file_path = self.worldview_dir / f"{name}.md"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            debug_logger.log_info('WorldviewBuilder', f'世界观已保存: {name}')
            print(f"✓ 世界观已保存: {file_path}")
            
            return True
            
        except Exception as e:
            debug_logger.log_error('WorldviewBuilder', f'保存世界观失败: {str(e)}', e)
            return False
    
    def delete_worldview(self, name: str) -> bool:
        """
        删除世界观文件
        
        Args:
            name: 世界观名称
            
        Returns:
            是否成功删除
        """
        try:
            file_path = self.worldview_dir / f"{name}.md"
            
            if file_path.exists():
                file_path.unlink()
                debug_logger.log_info('WorldviewBuilder', f'世界观已删除: {name}')
                return True
            else:
                debug_logger.log_warning('WorldviewBuilder', f'世界观文件不存在: {name}')
                return False
                
        except Exception as e:
            debug_logger.log_error('WorldviewBuilder', f'删除世界观失败: {str(e)}', e)
            return False
    
    def parse_worldview_to_modules(self, content: str, source_file: str = None) -> List[WorldviewModule]:
        """
        解析世界观内容为模块化知识块
        
        Args:
            content: 世界观 Markdown 内容
            source_file: 来源文件名
            
        Returns:
            世界观模块列表
        """
        modules = []
        
        # 解析二级和三级标题作为模块分隔
        # 匹配 ## 标题 或 ### 标题
        sections = re.split(r'\n(?=#{2,3}\s+)', content)
        
        current_category = "general"
        
        for section in sections:
            if not section.strip():
                continue
            
            # 提取标题（支持 ## 和 ###）
            title_match = re.match(r'^#{2,3}\s+(.+?)(?:\n|$)', section)
            if title_match:
                title = title_match.group(1).strip()
                section_content = section[title_match.end():].strip()
            else:
                title = "基本信息"
                section_content = section.strip()
            
            # 根据标题推断分类
            category = self._infer_category(title)
            
            # 创建模块
            if section_content:
                module = WorldviewModule(
                    name=title,
                    category=category,
                    content=section_content,
                    source_file=source_file,
                    metadata={
                        "parsed_at": datetime.now().isoformat()
                    }
                )
                modules.append(module)
        
        debug_logger.log_info('WorldviewBuilder', f'解析完成', {
            'source': source_file,
            'modules_count': len(modules)
        })
        
        return modules
    
    def _infer_category(self, title: str) -> str:
        """
        根据标题推断分类
        
        Args:
            title: 标题文本
            
        Returns:
            分类名称
        """
        title_lower = title.lower()
        
        # 关键字全部小写，确保匹配一致性
        category_keywords = {
            "general": ["基本", "简介", "概述", "世界", "背景"],
            "rules": ["规则", "法则", "限制", "物理", "魔法"],
            "locations": ["地点", "场所", "位置", "环境", "地理"],
            "characters": ["角色", "人物", "npc", "种族"],
            "events": ["事件", "历史", "时间", "故事"],
            "items": ["物品", "道具", "装备", "物体"],
            "culture": ["文化", "习俗", "社会", "传统"],
            "technology": ["科技", "技术", "工具", "发明"]
        }
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return category
        
        return "general"
    
    def create_worldview_from_natural_language(
        self,
        description: str,
        name: str = None,
        use_llm: bool = True
    ) -> str:
        """
        从自然语言描述创建世界观
        
        Args:
            description: 用户的自然语言描述
            name: 世界观名称（可选）
            use_llm: 是否使用 LLM 增强生成（默认 True）
            
        Returns:
            生成的 Markdown 世界观内容
        """
        if use_llm:
            return self._generate_worldview_with_llm(description, name)
        else:
            return self._generate_worldview_template(description, name)
    
    def _generate_worldview_template(self, description: str, name: str = None) -> str:
        """
        生成基础世界观模板
        
        Args:
            description: 描述
            name: 名称
            
        Returns:
            Markdown 内容
        """
        worldview_name = name or "自定义世界观"
        
        template = f"""# {worldview_name}

## 世界基本信息

**世界名称**：{worldview_name}

**描述**：{description}

**创建时间**：{datetime.now().strftime("%Y年%m月%d日")}

## 世界特征

### 1. 基本设定

{description}

### 2. 规则与限制

<!-- 在这里添加世界的规则和限制 -->

### 3. 重要地点

<!-- 在这里添加世界中的重要地点 -->

### 4. 重要人物

<!-- 在这里添加世界中的重要人物 -->

### 5. 历史事件

<!-- 在这里添加世界的历史事件 -->

## 世界观融入

### 对话中的体现

- 自然地融入对话中
- 保持一致性
- 根据上下文适当展示

---

*这个世界观由用户自然语言描述生成，可以直接编辑此文件进行修改。*
"""
        return template
    
    def _generate_worldview_with_llm(self, description: str, name: str = None) -> str:
        """
        使用 LLM 增强生成世界观
        
        Args:
            description: 用户描述
            name: 世界观名称
            
        Returns:
            生成的 Markdown 内容
        """
        import requests
        
        api_key = os.getenv('SILICONFLOW_API_KEY')
        api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        model_name = os.getenv('TOOL_MODEL_NAME', os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct'))
        
        if not api_key:
            debug_logger.log_warning('WorldviewBuilder', 'API密钥未配置，使用模板生成')
            return self._generate_worldview_template(description, name)
        
        prompt = f"""你是一个专业的世界观设计师。请根据以下用户描述，生成一个详细的 Markdown 格式世界观设定文档。

用户描述：
{description}

请生成一个完整的世界观文档，包含以下部分：
1. 世界基本信息（名称、时代背景、地理位置）
2. 世界特征（社会环境、文化氛围、日常生活）
3. 物理规则（基本物理、时间流逝）
4. 地点设定（常见场所、虚拟环境）
5. 社会关系（人际关系、交流方式）
6. 科技水平（可用科技、科技限制）
7. 特殊设定（独特元素、魔法系统等，如有）
8. 注意事项（保持真实感、一致性等）

请使用中文输出，格式为 Markdown。保持专业且有创意。"""

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的世界观设计师，擅长创建丰富、一致的虚拟世界设定。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 3000,
                'stream': False
            }
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                
                # 确保内容以标题开头
                if not content.startswith('#'):
                    worldview_name = name or "自定义世界观"
                    content = f"# {worldview_name}\n\n{content}"
                
                debug_logger.log_info('WorldviewBuilder', 'LLM 世界观生成成功')
                return content
            
        except Exception as e:
            debug_logger.log_error('WorldviewBuilder', f'LLM 生成失败: {str(e)}', e)
        
        # 失败时降级到模板
        return self._generate_worldview_template(description, name)
    
    async def sync_to_cognee(
        self,
        worldview_name: str = None,
        modules: List[WorldviewModule] = None
    ) -> bool:
        """
        将世界观同步到 Cognee 记忆系统
        
        Args:
            worldview_name: 世界观名称（加载并解析）
            modules: 或直接提供模块列表
            
        Returns:
            是否成功同步
        """
        if self.cognee_manager is None:
            debug_logger.log_warning('WorldviewBuilder', 'Cognee 管理器未配置，跳过同步')
            return False
        
        try:
            # 如果提供了世界观名称，加载并解析
            if worldview_name:
                content = self.load_worldview(worldview_name)
                modules = self.parse_worldview_to_modules(content, worldview_name)
            
            if not modules:
                debug_logger.log_warning('WorldviewBuilder', '没有模块需要同步')
                return False
            
            # 同步每个模块到 Cognee
            for module in modules:
                await self.cognee_manager.add_worldview(
                    worldview_content=f"[{module.category}] {module.name}: {module.content}",
                    category=module.category
                )
            
            # 构建知识图谱
            await self.cognee_manager.cognify()
            
            debug_logger.log_info('WorldviewBuilder', f'世界观已同步到 Cognee', {
                'modules_count': len(modules)
            })
            
            print(f"✓ {len(modules)} 个世界观模块已同步到 Cognee")
            return True
            
        except Exception as e:
            debug_logger.log_error('WorldviewBuilder', f'同步到 Cognee 失败: {str(e)}', e)
            return False
    
    def sync_to_knowledge_base(
        self,
        worldview_name: str = None,
        modules: List[WorldviewModule] = None
    ) -> int:
        """
        将世界观同步到现有知识库
        
        Args:
            worldview_name: 世界观名称
            modules: 或直接提供模块列表
            
        Returns:
            同步的模块数量
        """
        try:
            # 如果提供了世界观名称，加载并解析
            if worldview_name:
                content = self.load_worldview(worldview_name)
                modules = self.parse_worldview_to_modules(content, worldview_name)
            
            if not modules:
                return 0
            
            synced_count = 0
            
            for module in modules:
                # 查找或创建实体
                entity_uuid = self.db.find_or_create_entity(f"世界观_{module.name}")
                
                # 设置定义
                self.db.set_entity_definition(
                    entity_uuid=entity_uuid,
                    content=module.content,
                    type_=f"世界观-{self.CATEGORIES.get(module.category, module.category)}",
                    source=f"worldview:{module.source_file or 'manual'}",
                    confidence=1.0,
                    priority=80,
                    is_base_knowledge=False
                )
                
                synced_count += 1
            
            debug_logger.log_info('WorldviewBuilder', f'世界观已同步到知识库', {
                'synced_count': synced_count
            })
            
            print(f"✓ {synced_count} 个世界观模块已同步到知识库")
            return synced_count
            
        except Exception as e:
            debug_logger.log_error('WorldviewBuilder', f'同步到知识库失败: {str(e)}', e)
            return 0
    
    def get_worldview_for_prompt(self, name: str = None) -> str:
        """
        获取用于提示词的世界观内容
        
        Args:
            name: 世界观名称（如果为 None，使用默认世界观）
            
        Returns:
            格式化的世界观提示词
        """
        try:
            return self.prompt_manager.get_worldview_prompt(worldview_name=name)
        except FileNotFoundError:
            debug_logger.log_warning('WorldviewBuilder', f'世界观文件未找到: {name}')
            return ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取世界观统计信息
        
        Returns:
            统计信息字典
        """
        files = self.list_worldview_files()
        
        total_size = sum(f["size"] for f in files)
        
        return {
            "worldview_count": len(files),
            "total_size_kb": total_size / 1024,
            "worldview_dir": str(self.worldview_dir),
            "categories": list(self.CATEGORIES.keys())
        }


# 全局实例
_global_worldview_builder: Optional[WorldviewBuilder] = None


def get_worldview_builder(cognee_manager=None) -> WorldviewBuilder:
    """
    获取全局世界观构建器实例（单例模式）
    
    Args:
        cognee_manager: Cognee 记忆管理器（可选）
        
    Returns:
        WorldviewBuilder 实例
    """
    global _global_worldview_builder
    if _global_worldview_builder is None:
        _global_worldview_builder = WorldviewBuilder(cognee_manager=cognee_manager)
    return _global_worldview_builder


if __name__ == '__main__':
    print("=" * 60)
    print("世界观构建系统测试")
    print("=" * 60)
    
    builder = WorldviewBuilder()
    
    # 测试列出世界观
    print("\n可用的世界观文件:")
    files = builder.list_worldview_files()
    for f in files:
        print(f"  - {f['name']} ({f['size']} bytes)")
    
    # 测试统计信息
    print("\n统计信息:")
    stats = builder.get_statistics()
    print(f"  世界观数量: {stats['worldview_count']}")
    print(f"  总大小: {stats['total_size_kb']:.2f} KB")
    
    # 测试自然语言生成（模板）
    print("\n测试自然语言生成:")
    content = builder.create_worldview_from_natural_language(
        "一个充满魔法的中世纪世界，有精灵、矮人和人类共存",
        name="魔法世界",
        use_llm=False
    )
    print(f"生成内容长度: {len(content)} 字符")
    print(content[:500] + "...")
    
    print("\n✓ 测试完成")
