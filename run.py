import sys
import os

# 解决 Windows 下控制台输出乱码问题
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.debug_utils import install_debugger

# 将当前目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import PyQt5
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Install global exception handler and logger
install_debugger()

if __name__ == "__main__":
    # Fix for Qt platform plugin "windows" not found
    dirname = os.path.dirname(PyQt5.__file__)
    plugin_path = os.path.join(dirname, 'Qt5', 'plugins')
    os.environ['QT_PLUGIN_PATH'] = plugin_path

    # 启用高DPI缩放
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    
    # Import MainWindow here to ensure QApplication is created first
    from src.main_window import MainWindow
    
    # 设置应用程序字体
    font = app.font()
    font.setFamily("Segoe UI") # Windows 默认字体，类似 Apple 的 San Francisco
    font.setPointSize(10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    # 窗口启动时置于最上层并激活（符合人性化，非强制置顶）
    window.activateWindow()
    window.raise_()
    
    sys.exit(app.exec_())
