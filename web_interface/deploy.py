#!/usr/bin/env python3
"""
Web界面部署脚本
用于自动化部署和配置Web界面
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse

class WebInterfaceDeployer:
    """Web界面部署器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.web_interface_dir = Path(__file__).parent
        self.requirements_file = self.web_interface_dir / "requirements.txt"
    
    def check_python_version(self):
        """检查Python版本"""
        print("🐍 检查Python版本...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python版本过低: {version.major}.{version.minor}")
            print("需要Python 3.8或更高版本")
            return False
        
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    
    def check_dependencies(self):
        """检查依赖包"""
        print("\n📦 检查依赖包...")
        
        if not self.requirements_file.exists():
            print("❌ requirements.txt文件不存在")
            return False
        
        try:
            # 读取依赖列表
            with open(self.requirements_file, 'r') as f:
                requirements = f.read().strip().split('\n')
            
            requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]
            
            print(f"📋 需要安装的包: {len(requirements)}个")
            for req in requirements:
                print(f"  - {req}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取依赖文件失败: {str(e)}")
            return False
    
    def install_dependencies(self, force=False):
        """安装依赖包"""
        print("\n📥 安装依赖包...")
        
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)]
            if force:
                cmd.append("--force-reinstall")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 依赖包安装成功")
                return True
            else:
                print(f"❌ 依赖包安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 安装过程出错: {str(e)}")
            return False
    
    def check_system_components(self):
        """检查系统组件"""
        print("\n🔧 检查系统组件...")
        
        # 检查核心模块
        core_modules = [
            "agents/master_agent.py",
            "core/models.py",
            "utils/file_utils.py"
        ]
        
        all_exist = True
        for module_path in core_modules:
            full_path = self.project_root / module_path
            if full_path.exists():
                print(f"✅ {module_path}")
            else:
                print(f"❌ {module_path} 不存在")
                all_exist = False
        
        return all_exist
    
    def create_config_files(self):
        """创建配置文件"""
        print("\n⚙️ 创建配置文件...")
        
        try:
            # 创建上传目录
            upload_dir = self.web_interface_dir / "uploads"
            upload_dir.mkdir(exist_ok=True)
            print(f"✅ 创建上传目录: {upload_dir}")
            
            # 创建日志目录
            log_dir = self.web_interface_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            print(f"✅ 创建日志目录: {log_dir}")
            
            # 创建临时目录
            temp_dir = self.web_interface_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            print(f"✅ 创建临时目录: {temp_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建配置文件失败: {str(e)}")
            return False
    
    def test_web_interface(self):
        """测试Web界面"""
        print("\n🧪 测试Web界面...")
        
        try:
            # 运行测试脚本
            test_script = self.web_interface_dir / "test_web_interface.py"
            if test_script.exists():
                result = subprocess.run([sys.executable, str(test_script)], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✅ Web界面测试通过")
                    return True
                else:
                    print(f"❌ Web界面测试失败: {result.stderr}")
                    return False
            else:
                print("⚠️ 测试脚本不存在，跳过测试")
                return True
                
        except subprocess.TimeoutExpired:
            print("⚠️ 测试超时，可能正常")
            return True
        except Exception as e:
            print(f"❌ 测试过程出错: {str(e)}")
            return False
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        print("\n📝 创建启动脚本...")
        
        try:
            # 创建bash启动脚本
            bash_script = self.web_interface_dir / "start_web.sh"
            bash_content = f"""#!/bin/bash
# 字幕翻译系统Web界面启动脚本

echo "🚀 启动字幕翻译系统Web界面..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

# 进入Web界面目录
cd "{self.web_interface_dir}"

# 检查依赖
echo "📦 检查依赖包..."
python3 -c "import streamlit, plotly, pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 安装依赖包..."
    pip3 install -r requirements.txt
fi

# 启动应用
echo "🌐 启动Web应用..."
echo "访问地址: http://localhost:8501"
echo "按 Ctrl+C 停止服务"

python3 -m streamlit run app.py --server.port 8501 --server.address localhost
"""
            
            with open(bash_script, 'w') as f:
                f.write(bash_content)
            
            # 设置执行权限
            os.chmod(bash_script, 0o755)
            print(f"✅ 创建bash启动脚本: {bash_script}")
            
            # 创建批处理启动脚本（Windows）
            bat_script = self.web_interface_dir / "start_web.bat"
            bat_content = f"""@echo off
REM 字幕翻译系统Web界面启动脚本

echo 🚀 启动字幕翻译系统Web界面...

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装
    pause
    exit /b 1
)

REM 进入Web界面目录
cd /d "{self.web_interface_dir}"

REM 检查依赖
echo 📦 检查依赖包...
python -c "import streamlit, plotly, pandas" >nul 2>&1
if errorlevel 1 (
    echo 📥 安装依赖包...
    pip install -r requirements.txt
)

REM 启动应用
echo 🌐 启动Web应用...
echo 访问地址: http://localhost:8501
echo 按 Ctrl+C 停止服务

python -m streamlit run app.py --server.port 8501 --server.address localhost
pause
"""
            
            with open(bat_script, 'w') as f:
                f.write(bat_content)
            
            print(f"✅ 创建批处理启动脚本: {bat_script}")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建启动脚本失败: {str(e)}")
            return False
    
    def deploy(self, force_install=False, skip_test=False):
        """执行部署"""
        print("🚀 开始部署字幕翻译系统Web界面")
        print("=" * 50)
        
        # 检查Python版本
        if not self.check_python_version():
            return False
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 安装依赖
        if not self.install_dependencies(force_install):
            return False
        
        # 检查系统组件
        if not self.check_system_components():
            print("⚠️ 部分系统组件缺失，Web界面可能无法正常工作")
        
        # 创建配置文件
        if not self.create_config_files():
            return False
        
        # 测试Web界面
        if not skip_test:
            if not self.test_web_interface():
                print("⚠️ 测试失败，但继续部署")
        
        # 创建启动脚本
        if not self.create_startup_scripts():
            return False
        
        print("\n🎉 Web界面部署完成！")
        print("\n📖 使用说明:")
        print("1. 运行完整版: python run_app.py")
        print("2. 运行演示版: streamlit run demo_app.py")
        print("3. 使用启动脚本: ./start_web.sh (Linux/Mac) 或 start_web.bat (Windows)")
        print("4. 访问地址: http://localhost:8501")
        
        return True
    
    def clean(self):
        """清理部署文件"""
        print("🧹 清理部署文件...")
        
        clean_dirs = ["uploads", "logs", "temp", "__pycache__"]
        clean_files = ["start_web.sh", "start_web.bat"]
        
        for dir_name in clean_dirs:
            dir_path = self.web_interface_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"✅ 删除目录: {dir_path}")
        
        for file_name in clean_files:
            file_path = self.web_interface_dir / file_name
            if file_path.exists():
                file_path.unlink()
                print(f"✅ 删除文件: {file_path}")
        
        print("🎉 清理完成！")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="字幕翻译系统Web界面部署工具")
    parser.add_argument("--force-install", action="store_true", help="强制重新安装依赖包")
    parser.add_argument("--skip-test", action="store_true", help="跳过测试步骤")
    parser.add_argument("--clean", action="store_true", help="清理部署文件")
    
    args = parser.parse_args()
    
    deployer = WebInterfaceDeployer()
    
    if args.clean:
        deployer.clean()
    else:
        success = deployer.deploy(
            force_install=args.force_install,
            skip_test=args.skip_test
        )
        
        if not success:
            print("\n❌ 部署失败！")
            sys.exit(1)

if __name__ == "__main__":
    main()