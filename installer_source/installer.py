import sys
import os
import zipfile
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QProgressBar, QMessageBox, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class InstallThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, zip_path, install_dir):
        super().__init__()
        self.zip_path = zip_path
        self.install_dir = install_dir
        
    def run(self):
        try:
            if not os.path.exists(self.zip_path):
                self.finished.emit(False, "安装包文件丢失 (app_payload.zip)")
                return

            if not os.path.exists(self.install_dir):
                os.makedirs(self.install_dir)

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                total_files = len(zip_ref.infolist())
                for i, file in enumerate(zip_ref.infolist()):
                    zip_ref.extract(file, self.install_dir)
                    self.progress.emit(int((i / total_files) * 90))
            
            # Create Shortcut
            self.create_shortcut()
            self.progress.emit(100)
            self.finished.emit(True, "Installation Complete!")
            
        except Exception as e:
            self.finished.emit(False, str(e))
            
    def create_shortcut(self):
        try:
            # Look for the executable
            target = os.path.join(self.install_dir, "智能排班系统", "智能排班系统.exe")
            if not os.path.exists(target):
                 target = os.path.join(self.install_dir, "智能排班系统.exe")
            
            if not os.path.exists(target):
                print(f"Warning: Executable not found at {target}")
                return

            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') 
            link_path = os.path.join(desktop, "智能排班系统.lnk")
            
            # PowerShell command to create shortcut
            ps_script = f"""
            $ws = New-Object -ComObject WScript.Shell
            $s = $ws.CreateShortcut('{link_path}')
            $s.TargetPath = '{target}'
            $s.WorkingDirectory = '{os.path.dirname(target)}'
            $s.Save()
            """
            
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
            
        except Exception as e:
            print(f"Shortcut creation failed: {e}")

class Installer(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('智能排班系统 安装向导')
        self.setFixedSize(600, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                height: 6px;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("欢迎安装 智能排班系统")
        title.setFont(QFont('Microsoft YaHei', 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("请选择安装位置")
        desc.setFont(QFont('Microsoft YaHei', 12))
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Path Selection
        path_layout = QHBoxLayout()
        self.path_label = QLabel(os.path.join(os.environ['LOCALAPPDATA'], 'SmartScheduler'))
        self.path_label.setStyleSheet("border: 1px solid #ddd; padding: 10px; border-radius: 4px; color: #555;")
        path_layout.addWidget(self.path_label)
        
        btn_browse = QPushButton("更改...")
        btn_browse.clicked.connect(self.browse_folder)
        btn_browse.setFixedWidth(80)
        btn_browse.setStyleSheet("""
            background-color: #E5E5E5; 
            color: #333;
        """)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        
        layout.addStretch()
        
        # Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setVisible(False)
        layout.addWidget(self.pbar)
        
        # Install Button
        self.btn_install = QPushButton("立即安装")
        self.btn_install.setCursor(Qt.PointingHandCursor)
        self.btn_install.setMinimumHeight(45)
        self.btn_install.clicked.connect(self.start_install)
        layout.addWidget(self.btn_install)
        
        self.setLayout(layout)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择安装目录")
        if folder:
            self.path_label.setText(folder)
            
    def start_install(self):
        install_dir = self.path_label.text()
        if not install_dir:
            return
            
        self.btn_install.setEnabled(False)
        self.btn_install.setText("正在安装...")
        self.pbar.setVisible(True)
        
        zip_path = resource_path("app_payload.zip")
        
        self.thread = InstallThread(zip_path, install_dir)
        self.thread.progress.connect(self.pbar.setValue)
        self.thread.finished.connect(self.install_finished)
        self.thread.start()
        
    def install_finished(self, success, message):
        self.btn_install.setEnabled(True)
        if success:
            self.btn_install.setText("安装完成")
            self.btn_install.clicked.disconnect()
            self.btn_install.clicked.connect(self.close)
            QMessageBox.information(self, "完成", "安装成功！您现在可以在桌面找到快捷方式。")
        else:
            self.btn_install.setText("重试")
            QMessageBox.critical(self, "错误", f"安装失败: {message}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Installer()
    ex.show()
    sys.exit(app.exec_())
