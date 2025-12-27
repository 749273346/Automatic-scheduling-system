from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QStackedWidget, QLabel, QPushButton, 
                             QScrollArea, QFrame, QComboBox, QCheckBox, QFormLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont

class SystemSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.resize(800, 500)
        self.setModal(True)
        # Remove the context help button (?) from the title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                height: 40px;
                padding-left: 10px;
                border-radius: 6px;
                margin: 2px 5px;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #E5E5E5;
                color: #000;
            }
            QListWidget::item:hover {
                background-color: #EBEBEB;
            }
        """)
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Sidebar ---
        self.sidebar_container = QFrame()
        self.sidebar_container.setFixedWidth(200)
        self.sidebar_container.setStyleSheet("background-color: #F0F0F5; border-right: 1px solid #DCDCDC;")
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        # Search Box (Mockup)
        search_mockup = QPushButton("🔍 搜索")
        search_mockup.setStyleSheet("""
            text-align: left;
            padding-left: 10px;
            background-color: #E3E3E8;
            border: none;
            border-radius: 6px;
            color: #888;
            height: 28px;
        """)
        sidebar_layout.addWidget(search_mockup)
        sidebar_layout.addSpacing(10)
        
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.change_page)
        
        items = [
            ("⚙️  通用设置", 0),
            ("❓  常见问题", 1),
            ("ℹ️  关于软件", 2)
        ]
        
        for text, index in items:
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, index)
            self.list_widget.addItem(item)
            
        sidebar_layout.addWidget(self.list_widget)
        
        main_layout.addWidget(self.sidebar_container)
        
        # --- Right Content ---
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: white;")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Add Pages
        self.stacked_widget.addWidget(self.create_general_page())
        self.stacked_widget.addWidget(self.create_faq_page())
        self.stacked_widget.addWidget(self.create_about_page())
        
        main_layout.addWidget(self.content_area)

        # Set initial selection (must be done after stacked_widget is created)
        self.list_widget.setCurrentRow(0)

    def change_page(self, row):
        self.stacked_widget.setCurrentIndex(row)

    def create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        
        title = QLabel("通用设置")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Appearance
        group_box = QFrame()
        group_box.setStyleSheet("background-color: #F9F9F9; border-radius: 8px; padding: 15px;")
        gb_layout = QFormLayout(group_box)
        gb_layout.setSpacing(15)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["浅色模式", "深色模式 (开发中)", "跟随系统"])
        gb_layout.addRow("外观模式:", theme_combo)
        
        lang_combo = QComboBox()
        lang_combo.addItems(["简体中文", "English"])
        gb_layout.addRow("语言设置:", lang_combo)
        
        layout.addWidget(group_box)
        
        # Notifications
        group_box2 = QFrame()
        group_box2.setStyleSheet("background-color: #F9F9F9; border-radius: 8px; padding: 15px;")
        gb_layout2 = QFormLayout(group_box2)
        
        notif_check = QCheckBox("启用桌面通知")
        notif_check.setChecked(True)
        gb_layout2.addRow("通知:", notif_check)
        
        auto_update = QCheckBox("自动检查更新")
        auto_update.setChecked(True)
        gb_layout2.addRow("更新:", auto_update)
        
        layout.addWidget(group_box2)
        layout.addStretch()
        return page

    def create_faq_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)
        
        title = QLabel("常见问题 (FAQ)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        faqs = [
            ("Q: 为什么自动排班后某些日期是空的？", 
             "A: 可能是该日期所有人员均不可用（受黑名单、分组或优先等级限制）。请检查排班警告信息，适当放宽一级人员的约束条件。"),
            ("Q: 如何保证某人一定排在某天？", 
             "A: 请使用手动拖拽功能将该人员放入对应日期。手动安排的班次会被系统锁定，自动排班时不会移动或覆盖它。"),
            ("Q: 统计报表里的名字显示不全？", 
             "A: 如果人员较多，系统会自动旋转横坐标文字。您也可以尝试最大化窗口以获得更好的查看效果。"),
            ("Q: 如何修改人员颜色？", 
             "A: 在“人员管理”界面，点击人员对应的颜色块即可选择新颜色。"),
            ("Q: 自动排班总是失败怎么办？", 
             "A: 请尝试减少硬性约束（如一级人员的期望工作日），或者手动安排部分困难班次后再运行自动排班。")
        ]
        
        for q, a in faqs:
            item = QFrame()
            item.setStyleSheet("background-color: #F9F9F9; border-radius: 8px; padding: 15px;")
            l_layout = QVBoxLayout(item)
            
            q_label = QLabel(q)
            q_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #333;")
            q_label.setWordWrap(True)
            
            a_label = QLabel(a)
            a_label.setStyleSheet("font-size: 14px; color: #666; margin-top: 5px;")
            a_label.setWordWrap(True)
            
            l_layout.addWidget(q_label)
            l_layout.addWidget(a_label)
            content_layout.addWidget(item)
            
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        return page

    def create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10) # 整体间距调小
        
        # Logo Mockup
        logo = QLabel("📅")
        logo.setStyleSheet("font-size: 72px; margin-bottom: 5px;")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        
        name = QLabel("智能排班系统")
        name.setStyleSheet("font-size: 26px; font-weight: bold; color: #000;")
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)
        
        version = QLabel("Version 1.0.0")
        version.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 10px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # iOS-style Grouped List Container
        info_container = QFrame()
        info_container.setFixedWidth(360) 
        info_container.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; 
                border-radius: 10px; 
                border: 1px solid #E5E5E5;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)
        
        def create_info_row(label, text, is_last=False):
            row_widget = QWidget()
            row_widget.setFixedHeight(44) # 标准 iOS 列表行高
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(15, 0, 15, 0)
            
            # 使用一个容器来居中显示 key 和 value
            center_container = QWidget()
            center_layout = QHBoxLayout(center_container)
            center_layout.setContentsMargins(0, 0, 0, 0)
            center_layout.setSpacing(5) # 冒号和内容之间的间距
            
            lbl_key = QLabel(label)
            lbl_key.setStyleSheet("font-size: 14px; color: #000;")
            lbl_key.setAlignment(Qt.AlignCenter)
            
            lbl_val = QLabel(text)
            lbl_val.setStyleSheet("font-size: 14px; color: #888;")
            lbl_val.setAlignment(Qt.AlignCenter)
            
            center_layout.addWidget(lbl_key)
            center_layout.addWidget(lbl_val)
            
            row_layout.addStretch()
            row_layout.addWidget(center_container)
            row_layout.addStretch()
            
            # Container to hold row + separator
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(row_widget)
            
            if not is_last:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background-color: #E5E5E5; margin-left: 15px;") # Indented separator
                container_layout.addWidget(line)
                
            return container
            
        info_layout.addWidget(create_info_row("单位：", "汕头水电车间"))
        info_layout.addWidget(create_info_row("作者：", "杨昊"))
        info_layout.addWidget(create_info_row("技术指导：", "洪映森", is_last=True))
        
        layout.addWidget(info_container)
        
        desc = QLabel("为您提供最智能、高效的团队排班解决方案。")
        desc.setStyleSheet("margin-top: 15px; color: #888; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        copyright = QLabel("© 2025 Intelligent Scheduling Inc. All rights reserved.")
        copyright.setStyleSheet("margin-top: 5px; color: #AAA; font-size: 11px;")
        copyright.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright)
        
        layout.addStretch()
        return page
