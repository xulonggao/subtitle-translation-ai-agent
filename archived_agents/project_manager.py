"""
项目管理系统
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from config import get_logger

logger = get_logger("project_manager")


@dataclass
class ProjectConfig:
    """项目配置类"""
    project_id: str
    project_title: str
    genre: str
    description: str
    created_at: str
    updated_at: str
    status: str = "active"  # active, archived, deleted
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """从字典创建实例"""
        return cls(**data)


class ProjectManager:
    """项目管理器
    
    负责管理多个影视剧翻译项目的配置和生命周期
    """
    
    def __init__(self, projects_root: str = "projects"):
        self.projects_root = Path(projects_root)
        self.template_dir = self.projects_root / "project_template"
        self.projects_config_file = self.projects_root / "projects.json"
        
        # 确保目录存在
        self.projects_root.mkdir(exist_ok=True)
        
        # 加载项目配置
        self.projects_config = self._load_projects_config()
        
        logger.info("项目管理器初始化完成", 
                   projects_root=str(self.projects_root),
                   project_count=len(self.projects_config))
    
    def _load_projects_config(self) -> Dict[str, ProjectConfig]:
        """加载项目配置"""
        if not self.projects_config_file.exists():
            return {}
        
        try:
            with open(self.projects_config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    project_id: ProjectConfig.from_dict(config)
                    for project_id, config in data.items()
                }
        except Exception as e:
            logger.error("加载项目配置失败", error=str(e))
            return {}
    
    def _save_projects_config(self):
        """保存项目配置"""
        try:
            data = {
                project_id: config.to_dict()
                for project_id, config in self.projects_config.items()
            }
            with open(self.projects_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("项目配置已保存")
        except Exception as e:
            logger.error("保存项目配置失败", error=str(e))
            raise
    
    def create_project(self, 
                      project_id: str, 
                      project_title: str, 
                      genre: str, 
                      description: str = "") -> ProjectConfig:
        """创建新项目"""
        
        # 检查项目ID是否已存在
        if project_id in self.projects_config:
            raise ValueError(f"项目ID '{project_id}' 已存在")
        
        # 检查项目目录是否已存在
        project_dir = self.projects_root / project_id
        if project_dir.exists():
            raise ValueError(f"项目目录 '{project_dir}' 已存在")
        
        # 检查模板是否存在
        if not self.template_dir.exists():
            raise ValueError(f"项目模板不存在: {self.template_dir}")
        
        try:
            # 复制模板
            shutil.copytree(self.template_dir, project_dir)
            logger.info("项目模板复制完成", project_id=project_id, project_dir=str(project_dir))
            
            # 创建项目配置
            import datetime
            now = datetime.datetime.now().isoformat()
            
            project_config = ProjectConfig(
                project_id=project_id,
                project_title=project_title,
                genre=genre,
                description=description,
                created_at=now,
                updated_at=now
            )
            
            # 保存到内存和文件
            self.projects_config[project_id] = project_config
            self._save_projects_config()
            
            # 更新项目特定文件
            self._update_project_files(project_id, project_config)
            
            logger.info("项目创建成功", 
                       project_id=project_id,
                       project_title=project_title,
                       genre=genre)
            
            return project_config
            
        except Exception as e:
            # 清理失败的项目目录
            if project_dir.exists():
                shutil.rmtree(project_dir)
            logger.error("项目创建失败", project_id=project_id, error=str(e))
            raise
    
    def _update_project_files(self, project_id: str, config: ProjectConfig):
        """更新项目特定文件"""
        project_dir = self.projects_root / project_id
        
        # 更新story_context.md
        story_file = project_dir / "story_context.md"
        if story_file.exists():
            content = story_file.read_text(encoding='utf-8')
            content = content.replace("[填写剧名]", config.project_title)
            content = content.replace("[现代剧/古装剧/科幻剧/军旅剧等]", config.genre)
            story_file.write_text(content, encoding='utf-8')
        
        # 更新character_relations.json
        char_file = project_dir / "character_relations.json"
        if char_file.exists():
            with open(char_file, 'r', encoding='utf-8') as f:
                char_data = json.load(f)
            
            char_data["project_info"]["project_id"] = project_id
            char_data["project_info"]["project_title"] = config.project_title
            char_data["project_info"]["genre"] = config.genre
            char_data["project_info"]["description"] = config.description
            
            with open(char_file, 'w', encoding='utf-8') as f:
                json.dump(char_data, f, ensure_ascii=False, indent=2)
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """获取项目配置"""
        return self.projects_config.get(project_id)
    
    def list_projects(self, status: Optional[str] = None) -> List[ProjectConfig]:
        """列出所有项目"""
        projects = list(self.projects_config.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return sorted(projects, key=lambda x: x.updated_at, reverse=True)
    
    def update_project(self, project_id: str, **kwargs) -> ProjectConfig:
        """更新项目配置"""
        if project_id not in self.projects_config:
            raise ValueError(f"项目 '{project_id}' 不存在")
        
        config = self.projects_config[project_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # 更新时间
        import datetime
        config.updated_at = datetime.datetime.now().isoformat()
        
        # 保存配置
        self._save_projects_config()
        
        logger.info("项目配置已更新", project_id=project_id, updates=kwargs)
        return config
    
    def delete_project(self, project_id: str, permanent: bool = False):
        """删除项目"""
        if project_id not in self.projects_config:
            raise ValueError(f"项目 '{project_id}' 不存在")
        
        if permanent:
            # 永久删除
            project_dir = self.projects_root / project_id
            if project_dir.exists():
                shutil.rmtree(project_dir)
            
            del self.projects_config[project_id]
            self._save_projects_config()
            
            logger.info("项目已永久删除", project_id=project_id)
        else:
            # 标记为删除
            self.projects_config[project_id].status = "deleted"
            self._save_projects_config()
            
            logger.info("项目已标记为删除", project_id=project_id)
    
    def archive_project(self, project_id: str):
        """归档项目"""
        if project_id not in self.projects_config:
            raise ValueError(f"项目 '{project_id}' 不存在")
        
        self.projects_config[project_id].status = "archived"
        self._save_projects_config()
        
        logger.info("项目已归档", project_id=project_id)
    
    def restore_project(self, project_id: str):
        """恢复项目"""
        if project_id not in self.projects_config:
            raise ValueError(f"项目 '{project_id}' 不存在")
        
        self.projects_config[project_id].status = "active"
        self._save_projects_config()
        
        logger.info("项目已恢复", project_id=project_id)
    
    def get_project_path(self, project_id: str) -> Path:
        """获取项目目录路径"""
        if project_id not in self.projects_config:
            raise ValueError(f"项目 '{project_id}' 不存在")
        
        return self.projects_root / project_id
    
    def load_project_context(self, project_id: str) -> Dict[str, Any]:
        """加载项目上下文信息"""
        project_dir = self.get_project_path(project_id)
        context = {}
        
        # 加载剧情简介
        story_file = project_dir / "story_context.md"
        if story_file.exists():
            context["story_context"] = story_file.read_text(encoding='utf-8')
        
        # 加载人物关系
        char_file = project_dir / "character_relations.json"
        if char_file.exists():
            with open(char_file, 'r', encoding='utf-8') as f:
                context["character_relations"] = json.load(f)
        
        # 加载术语库
        term_file = project_dir / "terminology.json"
        if term_file.exists():
            with open(term_file, 'r', encoding='utf-8') as f:
                context["terminology"] = json.load(f)
        
        logger.info("项目上下文加载完成", 
                   project_id=project_id,
                   context_keys=list(context.keys()))
        
        return context
    
    def get_project_episodes(self, project_id: str) -> List[Path]:
        """获取项目的剧集文件"""
        project_dir = self.get_project_path(project_id)
        episodes_dir = project_dir / "episodes"
        
        if not episodes_dir.exists():
            return []
        
        # 查找SRT文件
        srt_files = list(episodes_dir.glob("*.srt"))
        return sorted(srt_files)
    
    def validate_project_structure(self, project_id: str) -> Dict[str, bool]:
        """验证项目结构完整性"""
        project_dir = self.get_project_path(project_id)
        
        required_files = [
            "story_context.md",
            "character_relations.json", 
            "terminology.json"
        ]
        
        validation_result = {}
        for file_name in required_files:
            file_path = project_dir / file_name
            validation_result[file_name] = file_path.exists()
        
        # 检查episodes目录
        episodes_dir = project_dir / "episodes"
        validation_result["episodes_dir"] = episodes_dir.exists()
        
        return validation_result


# 全局项目管理器实例
project_manager = ProjectManager()


def get_project_manager() -> ProjectManager:
    """获取项目管理器实例"""
    return project_manager