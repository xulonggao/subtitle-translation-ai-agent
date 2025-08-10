"""
项目管理系统测试
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from agents.project_manager import ProjectManager, ProjectConfig


class TestProjectConfig:
    """项目配置测试"""
    
    def test_project_config_creation(self):
        """测试项目配置创建"""
        config = ProjectConfig(
            project_id="test_project",
            project_title="测试项目",
            genre="现代剧",
            description="测试描述",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        
        assert config.project_id == "test_project"
        assert config.project_title == "测试项目"
        assert config.genre == "现代剧"
        assert config.status == "active"  # 默认值
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = ProjectConfig(
            project_id="test",
            project_title="测试",
            genre="现代剧",
            description="描述",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        
        data = config.to_dict()
        assert isinstance(data, dict)
        assert data["project_id"] == "test"
        assert data["project_title"] == "测试"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "project_id": "test",
            "project_title": "测试",
            "genre": "现代剧",
            "description": "描述",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "status": "active"
        }
        
        config = ProjectConfig.from_dict(data)
        assert config.project_id == "test"
        assert config.project_title == "测试"


class TestProjectManager:
    """项目管理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.projects_root = Path(self.temp_dir) / "projects"
        
        # 创建模板目录
        template_dir = self.projects_root / "project_template"
        template_dir.mkdir(parents=True)
        
        # 创建模板文件
        (template_dir / "story_context.md").write_text(
            "# [填写剧名]\n类型: [现代剧/古装剧/科幻剧/军旅剧等]",
            encoding='utf-8'
        )
        
        template_char_data = {
            "project_info": {
                "project_id": "template",
                "project_title": "模板",
                "genre": "通用",
                "description": "模板"
            }
        }
        with open(template_dir / "character_relations.json", 'w', encoding='utf-8') as f:
            json.dump(template_char_data, f, ensure_ascii=False, indent=2)
        
        (template_dir / "terminology.json").write_text('{}', encoding='utf-8')
        
        # 创建项目管理器
        self.manager = ProjectManager(str(self.projects_root))
    
    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.manager.projects_root == self.projects_root
        assert self.manager.template_dir.exists()
        assert isinstance(self.manager.projects_config, dict)
    
    def test_create_project_success(self):
        """测试成功创建项目"""
        project_id = "test_drama"
        project_title = "测试剧集"
        genre = "现代剧"
        description = "测试描述"
        
        config = self.manager.create_project(
            project_id=project_id,
            project_title=project_title,
            genre=genre,
            description=description
        )
        
        # 验证配置
        assert config.project_id == project_id
        assert config.project_title == project_title
        assert config.genre == genre
        assert config.description == description
        assert config.status == "active"
        
        # 验证项目目录
        project_dir = self.projects_root / project_id
        assert project_dir.exists()
        assert (project_dir / "story_context.md").exists()
        assert (project_dir / "character_relations.json").exists()
        assert (project_dir / "terminology.json").exists()
        
        # 验证文件内容更新
        story_content = (project_dir / "story_context.md").read_text(encoding='utf-8')
        assert project_title in story_content
        assert genre in story_content
        
        # 验证配置文件保存
        assert project_id in self.manager.projects_config
    
    def test_create_project_duplicate_id(self):
        """测试创建重复ID的项目"""
        project_id = "duplicate_test"
        
        # 第一次创建
        self.manager.create_project(
            project_id=project_id,
            project_title="第一个项目",
            genre="现代剧"
        )
        
        # 第二次创建应该失败
        with pytest.raises(ValueError, match="项目ID.*已存在"):
            self.manager.create_project(
                project_id=project_id,
                project_title="第二个项目",
                genre="古装剧"
            )
    
    def test_get_project(self):
        """测试获取项目"""
        # 创建项目
        project_id = "get_test"
        created_config = self.manager.create_project(
            project_id=project_id,
            project_title="获取测试",
            genre="现代剧"
        )
        
        # 获取项目
        retrieved_config = self.manager.get_project(project_id)
        assert retrieved_config is not None
        assert retrieved_config.project_id == created_config.project_id
        assert retrieved_config.project_title == created_config.project_title
        
        # 获取不存在的项目
        non_existent = self.manager.get_project("non_existent")
        assert non_existent is None
    
    def test_list_projects(self):
        """测试列出项目"""
        # 创建多个项目
        projects_data = [
            ("project1", "项目1", "现代剧"),
            ("project2", "项目2", "古装剧"),
            ("project3", "项目3", "科幻剧")
        ]
        
        for project_id, title, genre in projects_data:
            self.manager.create_project(project_id, title, genre)
        
        # 列出所有项目
        all_projects = self.manager.list_projects()
        assert len(all_projects) == 3
        
        # 验证排序（按更新时间倒序）
        project_ids = [p.project_id for p in all_projects]
        assert "project3" in project_ids  # 最后创建的应该在前面
        
        # 按状态筛选
        active_projects = self.manager.list_projects(status="active")
        assert len(active_projects) == 3
        
        archived_projects = self.manager.list_projects(status="archived")
        assert len(archived_projects) == 0
    
    def test_update_project(self):
        """测试更新项目"""
        # 创建项目
        project_id = "update_test"
        original_config = self.manager.create_project(
            project_id=project_id,
            project_title="原始标题",
            genre="现代剧"
        )
        
        original_updated_at = original_config.updated_at
        
        # 更新项目
        updated_config = self.manager.update_project(
            project_id=project_id,
            project_title="更新后标题",
            description="新的描述"
        )
        
        assert updated_config.project_title == "更新后标题"
        assert updated_config.description == "新的描述"
        assert updated_config.genre == "现代剧"  # 未更新的字段保持不变
        assert updated_config.updated_at != original_updated_at  # 更新时间应该改变
        
        # 更新不存在的项目
        with pytest.raises(ValueError, match="项目.*不存在"):
            self.manager.update_project("non_existent", project_title="新标题")
    
    def test_delete_project(self):
        """测试删除项目"""
        # 创建项目
        project_id = "delete_test"
        self.manager.create_project(project_id, "删除测试", "现代剧")
        
        project_dir = self.projects_root / project_id
        assert project_dir.exists()
        
        # 软删除
        self.manager.delete_project(project_id, permanent=False)
        assert self.manager.projects_config[project_id].status == "deleted"
        assert project_dir.exists()  # 目录仍然存在
        
        # 永久删除
        self.manager.delete_project(project_id, permanent=True)
        assert project_id not in self.manager.projects_config
        assert not project_dir.exists()  # 目录被删除
    
    def test_archive_and_restore_project(self):
        """测试归档和恢复项目"""
        # 创建项目
        project_id = "archive_test"
        self.manager.create_project(project_id, "归档测试", "现代剧")
        
        # 归档项目
        self.manager.archive_project(project_id)
        assert self.manager.projects_config[project_id].status == "archived"
        
        # 恢复项目
        self.manager.restore_project(project_id)
        assert self.manager.projects_config[project_id].status == "active"
    
    def test_load_project_context(self):
        """测试加载项目上下文"""
        # 创建项目
        project_id = "context_test"
        self.manager.create_project(project_id, "上下文测试", "现代剧")
        
        # 加载上下文
        context = self.manager.load_project_context(project_id)
        
        assert "story_context" in context
        assert "character_relations" in context
        assert "terminology" in context
        
        # 验证内容
        assert isinstance(context["story_context"], str)
        assert isinstance(context["character_relations"], dict)
        assert isinstance(context["terminology"], dict)
    
    def test_get_project_episodes(self):
        """测试获取项目剧集文件"""
        # 创建项目
        project_id = "episodes_test"
        self.manager.create_project(project_id, "剧集测试", "现代剧")
        
        # 创建episodes目录和文件
        project_dir = self.projects_root / project_id
        episodes_dir = project_dir / "episodes"
        episodes_dir.mkdir(exist_ok=True)
        
        # 创建SRT文件
        (episodes_dir / "ep01.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\n测试字幕")
        (episodes_dir / "ep02.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\n测试字幕2")
        (episodes_dir / "not_srt.txt").write_text("不是SRT文件")
        
        # 获取剧集文件
        episodes = self.manager.get_project_episodes(project_id)
        
        assert len(episodes) == 2
        assert all(ep.suffix == ".srt" for ep in episodes)
        assert any(ep.name == "ep01.srt" for ep in episodes)
        assert any(ep.name == "ep02.srt" for ep in episodes)
    
    def test_validate_project_structure(self):
        """测试验证项目结构"""
        # 创建项目
        project_id = "validate_test"
        self.manager.create_project(project_id, "验证测试", "现代剧")
        
        # 验证完整结构
        validation = self.manager.validate_project_structure(project_id)
        
        assert validation["story_context.md"] is True
        assert validation["character_relations.json"] is True
        assert validation["terminology.json"] is True
        assert validation["episodes_dir"] is False  # 默认不存在
        
        # 创建episodes目录
        project_dir = self.projects_root / project_id
        (project_dir / "episodes").mkdir()
        
        # 重新验证
        validation = self.manager.validate_project_structure(project_id)
        assert validation["episodes_dir"] is True
    
    def test_projects_config_persistence(self):
        """测试项目配置持久化"""
        # 创建项目
        project_id = "persistence_test"
        self.manager.create_project(project_id, "持久化测试", "现代剧")
        
        # 验证配置文件存在
        config_file = self.projects_root / "projects.json"
        assert config_file.exists()
        
        # 创建新的管理器实例
        new_manager = ProjectManager(str(self.projects_root))
        
        # 验证配置被正确加载
        assert project_id in new_manager.projects_config
        loaded_config = new_manager.get_project(project_id)
        assert loaded_config.project_title == "持久化测试"


def test_global_project_manager():
    """测试全局项目管理器"""
    from agents.project_manager import get_project_manager
    
    manager = get_project_manager()
    assert isinstance(manager, ProjectManager)
    
    # 多次调用应该返回同一个实例
    manager2 = get_project_manager()
    assert manager is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])