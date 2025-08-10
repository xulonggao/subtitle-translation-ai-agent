#!/usr/bin/env python3
"""
命令行工具
"""
import click
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger, system_config


@click.group()
def cli():
    """影视剧字幕翻译Agent系统命令行工具"""
    setup_logging()


@cli.command()
def status():
    """显示系统状态"""
    logger = get_logger("cli")
    logger.info("检查系统状态...")
    
    click.echo("🎬 影视剧字幕翻译Agent系统")
    click.echo("=" * 40)
    click.echo(f"环境: {system_config.environment}")
    click.echo(f"调试模式: {system_config.debug}")
    click.echo(f"最大并发数: {system_config.max_concurrent_translations}")
    click.echo(f"批量大小: {system_config.batch_size}")
    click.echo(f"上下文窗口: {system_config.context_window_size}")
    click.echo("=" * 40)
    
    # 检查项目目录
    projects_dir = Path("projects")
    if projects_dir.exists():
        projects = [p.name for p in projects_dir.iterdir() if p.is_dir() and p.name != "__pycache__"]
        click.echo(f"可用项目: {', '.join(projects)}")
    else:
        click.echo("未找到项目目录")
    
    click.echo("系统状态: ✅ 正常")


@cli.command()
@click.argument('project_name')
@click.option('--title', prompt='项目标题', help='项目标题')
@click.option('--genre', prompt='项目类型', help='项目类型（如：现代剧、古装剧、军旅剧等）')
@click.option('--description', default='', help='项目描述')
def create_project(project_name, title, genre, description):
    """创建新项目"""
    logger = get_logger("cli")
    logger.info(f"创建新项目: {project_name}")
    
    try:
        from agents.project_manager import get_project_manager
        manager = get_project_manager()
        
        config = manager.create_project(
            project_id=project_name,
            project_title=title,
            genre=genre,
            description=description
        )
        
        click.echo(f"✅ 项目 {project_name} 创建成功")
        click.echo(f"项目标题: {config.project_title}")
        click.echo(f"项目类型: {config.genre}")
        click.echo(f"项目目录: {manager.get_project_path(project_name)}")
        click.echo("\n请编辑以下文件:")
        click.echo("- story_context.md (剧情简介)")
        click.echo("- character_relations.json (人物关系)")
        click.echo("- terminology.json (术语库)")
        
    except Exception as e:
        click.echo(f"❌ 创建项目失败: {e}")


@cli.command()
@click.option('--status', help='按状态筛选项目 (active, archived, deleted)')
def list_projects(status):
    """列出所有项目"""
    try:
        from agents.project_manager import get_project_manager
        manager = get_project_manager()
        
        projects = manager.list_projects(status=status)
        
        if projects:
            click.echo(f"项目列表 ({len(projects)} 个项目):")
            for project in projects:
                status_icon = {
                    'active': '🟢',
                    'archived': '📦',
                    'deleted': '🗑️'
                }.get(project.status, '❓')
                
                click.echo(f"  {status_icon} {project.project_id}")
                click.echo(f"     标题: {project.project_title}")
                click.echo(f"     类型: {project.genre}")
                click.echo(f"     状态: {project.status}")
                if project.description:
                    click.echo(f"     描述: {project.description}")
                click.echo()
        else:
            status_text = f"状态为 {status} 的" if status else ""
            click.echo(f"暂无{status_text}项目")
            
    except Exception as e:
        click.echo(f"❌ 列出项目失败: {e}")


@cli.command()
@click.argument('project_name')
def show_project(project_name):
    """显示项目信息"""
    try:
        from agents.project_manager import get_project_manager
        manager = get_project_manager()
        
        # 获取项目配置
        config = manager.get_project(project_name)
        if not config:
            click.echo(f"❌ 项目 {project_name} 不存在")
            return
        
        click.echo(f"📁 项目: {project_name}")
        click.echo("=" * 40)
        click.echo(f"标题: {config.project_title}")
        click.echo(f"类型: {config.genre}")
        click.echo(f"状态: {config.status}")
        click.echo(f"描述: {config.description}")
        click.echo(f"创建时间: {config.created_at}")
        click.echo(f"更新时间: {config.updated_at}")
        
        # 验证项目结构
        click.echo("\n📋 项目结构:")
        validation = manager.validate_project_structure(project_name)
        for file_name, exists in validation.items():
            status = "✅" if exists else "❌"
            click.echo(f"  {status} {file_name}")
        
        # 显示剧集文件
        episodes = manager.get_project_episodes(project_name)
        if episodes:
            click.echo(f"\n🎬 剧集文件 ({len(episodes)} 个):")
            for episode in episodes:
                click.echo(f"  📄 {episode.name}")
        else:
            click.echo("\n🎬 剧集文件: 暂无")
        
        # 显示剧情简介摘要
        try:
            context = manager.load_project_context(project_name)
            if "story_context" in context:
                click.echo("\n📖 剧情简介摘要:")
                lines = context["story_context"].split('\n')[:5]
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        click.echo(f"  {line.strip()}")
                        break
        except Exception:
            pass
            
    except Exception as e:
        click.echo(f"❌ 显示项目信息失败: {e}")


@cli.command()
def test():
    """运行测试"""
    click.echo("🧪 运行测试...")
    try:
        import subprocess
        result = subprocess.run(["python", "-m", "pytest", "tests/", "-v"], 
                              capture_output=True, text=True)
        click.echo(result.stdout)
        if result.stderr:
            click.echo(result.stderr)
        
        if result.returncode == 0:
            click.echo("✅ 所有测试通过")
        else:
            click.echo("❌ 测试失败")
    except Exception as e:
        click.echo(f"❌ 运行测试失败: {e}")


@cli.command()
def install():
    """安装依赖"""
    click.echo("📦 安装依赖...")
    try:
        import subprocess
        result = subprocess.run(["pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True)
        click.echo(result.stdout)
        if result.stderr:
            click.echo(result.stderr)
        
        if result.returncode == 0:
            click.echo("✅ 依赖安装完成")
        else:
            click.echo("❌ 依赖安装失败")
    except Exception as e:
        click.echo(f"❌ 安装依赖失败: {e}")


if __name__ == "__main__":
    cli()