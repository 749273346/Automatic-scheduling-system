import os
import shutil
import subprocess
import sys

def package_app():
    # 1. Clean previous build
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    # 2. Run PyInstaller
    # --onedir: Create a directory with the executable (easier for troubleshooting and includes dependencies)
    # --windowed: No console window
    # --name: Name of the executable
    # --add-data: Include resources folder
    # --clean: Clean cache
    print("Running PyInstaller...")
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--clean',
        '--name', '智能排班系统',
        '--add-data', 'resources;resources',
        'run.py'
    ]
    
    subprocess.check_call(cmd)

    # 3. Post-processing: Copy additional files to dist folder
    dist_dir = os.path.join('dist', '智能排班系统')
    
    print("Copying additional files...")
    
    # Copy '项目信息' folder
    project_info_src = '项目信息'
    project_info_dst = os.path.join(dist_dir, '项目信息')
    if os.path.exists(project_info_src):
        shutil.copytree(project_info_src, project_info_dst)
        print(f"Copied {project_info_src} to {project_info_dst}")
    
    # Copy README.md
    if os.path.exists('README.md'):
        shutil.copy('README.md', os.path.join(dist_dir, 'README.md'))
        print("Copied README.md")

    print(f"\nPackaging complete! You can find the application in: {os.path.abspath(dist_dir)}")
    print(f"Run {os.path.join(dist_dir, '智能排班系统.exe')} to start the application.")

if __name__ == "__main__":
    package_app()
