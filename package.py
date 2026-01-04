import os
import shutil
import subprocess
import zipfile
import sys

def clean_build_dirs():
    print("Cleaning build directories...")
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
def build_main_app():
    print("Building main application...")
    # Using PyInstaller to build the main app into dist/智能排班系统
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--clean',
        '--name', '智能排班系统',
        '--add-data', 'resources;resources',
        '--icon', 'resources/icon.ico',
        'run.py'
    ]
    subprocess.check_call(cmd)

def copy_extra_resources():
    print("Copying extra resources...")
    # Source file
    extra_file_rel = r"项目相关资源\电力二工区人员信息 （最新）.xlsx"
    extra_file_abs = os.path.abspath(extra_file_rel)
    
    # Destination: dist/智能排班系统/电力二工区人员信息 （最新）.xlsx
    dest_dir = os.path.join('dist', '智能排班系统')
    
    if not os.path.exists(extra_file_abs):
        print(f"Warning: Extra file not found at {extra_file_abs}")
        # List dir to help debug if fails
        print(f"Listing {os.path.dirname(extra_file_abs)}:")
        try:
            print(os.listdir(os.path.dirname(extra_file_abs)))
        except:
            pass
        return

    shutil.copy2(extra_file_abs, dest_dir)
    print(f"Copied {extra_file_rel} to {dest_dir}")

def copy_docs():
    print("Copying documentation...")
    dest_dir = os.path.join('dist', '智能排班系统')
    
    # Copy 说明文档.md
    if os.path.exists('说明文档.md'):
        shutil.copy2('说明文档.md', dest_dir)
        
    # Copy 项目信息 folder
    project_info_src = '项目信息'
    project_info_dest = os.path.join(dest_dir, '项目信息')
    if os.path.exists(project_info_src):
        if os.path.exists(project_info_dest):
            shutil.rmtree(project_info_dest)
        shutil.copytree(project_info_src, project_info_dest)
        
    print("Docs copied.")

def create_payload_zip():
    print("Creating payload zip...")
    source_dir = os.path.join('dist', '智能排班系统')
    zip_path = os.path.join('build', 'app_payload.zip')
    
    if not os.path.exists('build'):
        os.makedirs('build')
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # The zip should contain '智能排班系统/...'
                # So we want relpath from 'dist'
                arcname = os.path.relpath(file_path, 'dist')
                zf.write(file_path, arcname)
                
    print(f"Payload created at {zip_path}")
    return zip_path

def build_installer(payload_path):
    print("Building installer executable...")
    
    installer_script = os.path.join('installer_source', 'installer.py')
    
    # Payload path must be absolute or correct relative for PyInstaller
    # payload_path is 'build\app_payload.zip'
    
    add_data_arg = f"{payload_path};."
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--clean',
        '--name', '智能排班系统_安装包',
        '--add-data', add_data_arg,
        '--icon', 'resources/icon.ico',
        installer_script
    ]
    
    subprocess.check_call(cmd)
    
    print("Installer build complete.")
    print(f"Installer available at: {os.path.abspath(os.path.join('dist', '智能排班系统_安装包.exe'))}")
    return os.path.join('dist', '智能排班系统_安装包.exe')

def create_final_release_zip(installer_path):
    print("Creating final release zip...")
    release_zip_path = os.path.join('dist', '智能排班系统_安装包.zip')
    
    with zipfile.ZipFile(release_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(installer_path, os.path.basename(installer_path))
        # Add a Readme if exists
        if os.path.exists('README.md'):
            zf.write('README.md', 'README.md')
        # Add 说明文档.md if exists
        if os.path.exists('说明文档.md'):
            zf.write('说明文档.md', '说明文档.md')
            
    print(f"Final release zip created at: {os.path.abspath(release_zip_path)}")
    return release_zip_path

def deploy_to_desktop(zip_path):
    target_dir = r"C:\Users\74927\Desktop\智能排班系统"
    print(f"Deploying to {target_dir}...")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    shutil.copy2(zip_path, target_dir)
    print(f"Successfully deployed package to: {target_dir}")

if __name__ == "__main__":
    clean_build_dirs()
    build_main_app()
    copy_extra_resources()
    copy_docs()
    payload_zip = create_payload_zip()
    installer_exe = build_installer(payload_zip)
    final_zip = create_final_release_zip(installer_exe)
    # deploy_to_desktop(final_zip) # Optional, can be commented out if not needed or fails
