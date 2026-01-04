import sys
import traceback
import logging
import datetime
import os
from PyQt5.QtWidgets import QMessageBox, QApplication

def setup_logging():
    """配置日志系统"""
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_filename = os.path.join(log_dir, f"crash_log_{datetime.date.today()}.txt")
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return log_filename

def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常捕获器：记录日志并弹窗提示"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 1. 获取详细堆栈信息
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # 2. 记录到文件日志
    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # 3. 控制台输出 (方便开发时实时看)
    print(f"CRITICAL ERROR: {exc_value}", file=sys.stderr)
    print(error_msg, file=sys.stderr)

    # 4. GUI 弹窗提示 (如果 GUI 已启动)
    app = QApplication.instance()
    if app:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText("系统遇到严重错误 (System Error)")
        
        # 提取最后一行错误信息作为简述
        short_error = str(exc_value)
        msg_box.setInformativeText(
            f"程序无法继续运行。\n"
            f"错误详情已保存至日志文件。\n\n"
            f"错误摘要: {short_error}"
        )
        
        # 详细信息放入折叠区域
        msg_box.setDetailedText(error_msg)
        msg_box.setWindowTitle("系统崩溃报告")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

def install_debugger():
    """安装全局调试器"""
    try:
        log_file = setup_logging()
        sys.excepthook = handle_exception
        print(f"[INFO] [DebugSystem] 调试系统已启动。错误日志将保存至: {log_file}")
    except Exception as e:
        print(f"[ERROR] [DebugSystem] 无法初始化日志系统: {e}")
