import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QHeaderView, QInputDialog, QColorDialog, QMessageBox, QLabel, QSpinBox, QGroupBox,
                             QDialog, QTabWidget, QCalendarWidget, QCheckBox, QComboBox, QLineEdit, QFormLayout, QDialogButtonBox, QSpacerItem, QSizePolicy,
                             QScrollArea, QGridLayout, QListWidget, QListWidgetItem, QMenu, QAction, QFileDialog, QProgressDialog, QAbstractItemView, QFrame, QButtonGroup, QRadioButton, QDateEdit, QAbstractSpinBox, QStackedWidget)
from PyQt5.QtCore import Qt, QLocale, QSize, pyqtSignal, QDate
from PyQt5.QtGui import QColor, QIcon, QFont, QCursor
import openpyxl
import random
from src.models import User
from src.db_manager import DBManager
from src.rules_manager import RulesManager

# --- Modern UI Components ---

class CardWidget(QFrame):
    """Base class for card-style widgets"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("CardWidget")
        self.setStyleSheet("""
            QFrame#CardWidget {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E5EA;
            }
            QFrame#CardWidget:hover {
                border: 1px solid #007AFF;
                background-color: #F9F9FB;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class WeeklyRuleCard(CardWidget):
    """Card representing a day's schedule rule"""
    def __init__(self, day_index, day_name, parent=None):
        super().__init__(parent)
        self.day_index = day_index
        self.day_name = day_name
        self.mode = "loop"
        self.users = []
        self.user_objs = [] # List of User objects for display
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Header: Day Name
        self.lbl_day = QLabel(self.day_name)
        self.lbl_day.setStyleSheet("font-size: 18px; font-weight: bold; color: #1D1D1F;")
        layout.addWidget(self.lbl_day)
        
        # Mode Badge
        self.lbl_mode = QLabel("循环填充")
        self.lbl_mode.setStyleSheet("""
            background-color: #E5F1FB; 
            color: #007AFF; 
            border-radius: 6px; 
            padding: 4px 8px; 
            font-size: 12px;
            font-weight: 600;
        """)
        self.lbl_mode.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(self.lbl_mode)
        
        # Users Summary
        self.lbl_users = QLabel("自动从循环池填充")
        self.lbl_users.setWordWrap(True)
        self.lbl_users.setStyleSheet("font-size: 13px; color: #86868B; margin-top: 5px;")
        layout.addWidget(self.lbl_users)
        
        layout.addStretch()
        
        # Indicator Line at bottom
        self.indicator = QFrame()
        self.indicator.setFixedHeight(4)
        self.indicator.setStyleSheet("background-color: #E5E5EA; border-radius: 2px;")
        layout.addWidget(self.indicator)
        
    def update_state(self, mode, users, user_lookup_func):
        self.mode = mode
        self.users = users
        self.user_objs = [user_lookup_func(u) for u in users]
        
        # Update Mode Label & Indicator
        if mode == "fixed":
            self.lbl_mode.setText("固定人员")
            self.lbl_mode.setStyleSheet("background-color: #E8F5E9; color: #34C759; border-radius: 6px; padding: 4px 8px;")
            self.indicator.setStyleSheet("background-color: #34C759;")
        elif mode == "rotation":
            self.lbl_mode.setText("轮班模式")
            self.lbl_mode.setStyleSheet("background-color: #FFF3E0; color: #FF9500; border-radius: 6px; padding: 4px 8px;")
            self.indicator.setStyleSheet("background-color: #FF9500;")
        elif mode == "follow_saturday":
            self.lbl_mode.setText("跟随周六")
            self.lbl_mode.setStyleSheet("background-color: #F2F2F7; color: #8E8E93; border-radius: 6px; padding: 4px 8px;")
            self.indicator.setStyleSheet("background-color: #8E8E93;")
        else: # loop
            self.lbl_mode.setText("循环填充")
            self.lbl_mode.setStyleSheet("background-color: #E5F1FB; color: #007AFF; border-radius: 6px; padding: 4px 8px;")
            self.indicator.setStyleSheet("background-color: #007AFF;")
            
        # Update Users Text
        if self.day_name == "周日":
             self.lbl_users.setText("自动与周六保持一致 (2人)")
             self.lbl_mode.setText("跟随周六") # Force visual
             self.lbl_mode.setStyleSheet("background-color: #F2F2F7; color: #8E8E93; border-radius: 6px; padding: 4px 8px;")
        elif mode == "loop":
            self.lbl_users.setText("自动从下方循环池按顺序填充 (2人)")
        elif mode == "follow_saturday":
            self.lbl_users.setText("与周六排班人员保持一致")
        elif mode == "rotation":
            names = [u.name if u else "?" for u in self.user_objs]
            if len(names) >= 2:
                self.lbl_users.setText(f"单周: {names[0]}\n双周: {names[1]}")
            else:
                self.lbl_users.setText("请配置轮班人员\n剩余名额自动循环填充")
        elif mode == "fixed":
            names = [u.name if u else "?" for u in self.user_objs]
            if names:
                txt = "、".join(names)
                if len(names) < 2:
                    txt += "\n(+1人循环填充)"
                self.lbl_users.setText(txt)
            else:
                self.lbl_users.setText("请选择固定值班人员\n(不足2人将自动补齐)")

class ModeOptionWidget(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, mode_key, title, desc, icon, parent=None):
        super().__init__(parent)
        self.mode_key = mode_key
        self.setCursor(Qt.PointingHandCursor)
        self.selected = False
        
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        # Title
        self.lbl_title = QLabel(f"{icon}  {title}")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #1D1D1F; background: transparent; border: none;")
        layout.addWidget(self.lbl_title)
        
        # Description
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("font-size: 12px; color: #86868B; background: transparent; border: none;")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)
        
        self.update_style()
        
    def set_selected(self, selected):
        self.selected = selected
        self.update_style()
        
    def update_style(self):
        if self.selected:
            self.setStyleSheet("""
                ModeOptionWidget {
                    border: 2px solid #007AFF;
                    border-radius: 10px;
                    background-color: #F0F8FF;
                }
            """)
        else:
            self.setStyleSheet("""
                ModeOptionWidget {
                    border: 1px solid #E5E5EA;
                    border-radius: 10px;
                    background-color: white;
                }
                ModeOptionWidget:hover {
                    background-color: #F9F9FB;
                    border: 1px solid #007AFF;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_key)

class DayConfigDialog(QDialog):
    """Modern configuration dialog for a specific day"""
    def __init__(self, day_name, current_mode, current_users, all_users, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"配置 {day_name} 排班规则")
        self.resize(500, 600)
        self.day_name = day_name
        self.mode = current_mode
        self.selected_users = list(current_users)
        self.all_users = all_users
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Mode Selection
        lbl_mode = QLabel("选择排班模式")
        lbl_mode.setStyleSheet("font-size: 16px; font-weight: bold; color: #1D1D1F;")
        layout.addWidget(lbl_mode)
        
        self.mode_widgets = {}
        
        mode_layout = QGridLayout()
        mode_layout.setSpacing(15)
        
        modes = [
            ("loop", "循环填充", "从人员池自动轮循", "🔄"),
            ("fixed", "固定人员", "指定专人值班", "🔒"),
            ("rotation", "轮班模式", "单双周交替轮换", "⚖️"),
            ("follow_saturday", "跟随周六", "与周六保持一致", "➡️")
        ]
        
        for idx, (mode_key, title, desc, icon) in enumerate(modes):
            widget = ModeOptionWidget(mode_key, title, desc, icon)
            widget.clicked.connect(self.on_mode_clicked)
            
            if mode_key == self.mode:
                widget.set_selected(True)
                
            self.mode_widgets[mode_key] = widget
            mode_layout.addWidget(widget, idx // 2, idx % 2)
            
        layout.addLayout(mode_layout)
        
        # 2. User Selection Area (Dynamic)
        self.config_area = QWidget()
        self.config_area.setStyleSheet("background-color: #F5F5F7; border-radius: 10px; padding: 15px;")
        self.config_layout = QVBoxLayout(self.config_area)
        layout.addWidget(self.config_area)
        
        self.update_config_area()
        
        # 3. Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(100, 36)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("确认")
        btn_save.setFixedSize(100, 36)
        btn_save.setProperty("class", "primary") # Use primary style
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #007AFF; 
                color: white; 
                border-radius: 18px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0062CC; }
        """)
        btn_save.clicked.connect(self.save_and_accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def on_mode_clicked(self, mode_key):
        if mode_key != self.mode:
            # Deselect old
            if self.mode in self.mode_widgets:
                self.mode_widgets[self.mode].set_selected(False)
            
            self.mode = mode_key
            
            # Select new
            if self.mode in self.mode_widgets:
                self.mode_widgets[self.mode].set_selected(True)
                
            self.update_config_area()

    def update_config_area(self):
        # Clear previous widgets
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if self.mode == "loop":
            lbl = QLabel("在此模式下，系统将从全局配置的“循环池”中按顺序自动指派人员，直到凑齐每日所需人数 (2人)。")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #666; font-size: 13px;")
            self.config_layout.addWidget(lbl)
            
        elif self.mode == "follow_saturday":
            lbl = QLabel("在此模式下，当天的值班人员将自动与“周六”的值班人员保持一致。\n常用于周日跟随周六，实现周末连班。")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #666; font-size: 13px;")
            self.config_layout.addWidget(lbl)
            
        elif self.mode == "fixed":
            lbl = QLabel("请选择固定值班人员 (可多选，建议1-2人):")
            self.config_layout.addWidget(lbl)
            lbl_hint = QLabel("若选择不足2人，剩余名额将自动从循环池填充。")
            lbl_hint.setStyleSheet("color: #86868B; font-size: 12px;")
            self.config_layout.addWidget(lbl_hint)
            
            self.user_list = QListWidget()
            self.user_list.setSelectionMode(QAbstractItemView.MultiSelection)
            self.user_list.setStyleSheet("background-color: white; border: 1px solid #DDD; border-radius: 6px;")
            
            for user in self.all_users:
                item = QListWidgetItem(f"{user.name} ({user.code})")
                item.setData(Qt.UserRole, user.code)
                self.user_list.addItem(item)
                if user.code in self.selected_users:
                    item.setSelected(True)
            
            self.config_layout.addWidget(self.user_list)
            
        elif self.mode == "rotation":
            lbl = QLabel("请依次配置轮班人员 (针对其中1个名额):")
            self.config_layout.addWidget(lbl)
            lbl_hint = QLabel("轮班人员占用1个名额，另1个名额将从循环池自动填充。")
            lbl_hint.setStyleSheet("color: #86868B; font-size: 12px;")
            self.config_layout.addWidget(lbl_hint)
            
            # Slot 1: Odd Week
            h1 = QHBoxLayout()
            h1.addWidget(QLabel("单周 (Odd):"))
            self.combo_odd = QComboBox()
            self.combo_odd.addItem("未选择", None)
            
            # Slot 2: Even Week
            h2 = QHBoxLayout()
            h2.addWidget(QLabel("双周 (Even):"))
            self.combo_even = QComboBox()
            self.combo_even.addItem("未选择", None)
            
            for user in self.all_users:
                self.combo_odd.addItem(user.name, user.code)
                self.combo_even.addItem(user.name, user.code)
            
            # Set current values
            if len(self.selected_users) > 0:
                idx = self.combo_odd.findData(self.selected_users[0])
                if idx >= 0: self.combo_odd.setCurrentIndex(idx)
            
            if len(self.selected_users) > 1:
                idx = self.combo_even.findData(self.selected_users[1])
                if idx >= 0: self.combo_even.setCurrentIndex(idx)
                
            h1.addWidget(self.combo_odd)
            h2.addWidget(self.combo_even)
            
            self.config_layout.addLayout(h1)
            self.config_layout.addLayout(h2)
            self.config_layout.addWidget(QLabel("注: 若需更多人轮班，请联系管理员扩展功能"))

    def save_and_accept(self):
        if self.mode == "fixed":
            self.selected_users = []
            for item in self.user_list.selectedItems():
                self.selected_users.append(item.data(Qt.UserRole))
        elif self.mode == "rotation":
            u1 = self.combo_odd.currentData()
            u2 = self.combo_even.currentData()
            self.selected_users = []
            if u1: self.selected_users.append(u1)
            if u2: self.selected_users.append(u2)
        elif self.mode in ["loop", "follow_saturday"]:
            self.selected_users = []
            
        self.accept()

# --- Legacy Dialog retained but new classes used above ---
class UserSelectionDialog(QDialog):
    def __init__(self, users, selected_codes=None, parent=None, title="选择人员"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        self.users = users
        self.selected_codes = set(selected_codes or [])
        
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        
        for user in self.users:
            item = QListWidgetItem(f"{user.name} ({user.code})")
            item.setData(Qt.UserRole, user.code)
            self.list_widget.addItem(item)
            if user.code in self.selected_codes:
                item.setSelected(True)
                
        layout.addWidget(self.list_widget)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def get_selected_codes(self):
        codes = []
        for item in self.list_widget.selectedItems():
            codes.append(item.data(Qt.UserRole))
        return codes

class UserDialog(QDialog):
    def __init__(self, user=None, parent=None, on_delete=None):
        super().__init__(parent)
        self.user = user
        self.mode = "edit" if user else "add"
        self.on_delete = on_delete
        self.setWindowTitle("编辑人员信息" if self.mode == "edit" else "添加人员")
        self.resize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_lbl = QLabel("人员信息" if self.mode == "edit" else "新人员信息")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #1D1D1F;")
        layout.addWidget(title_lbl)
        
        # Form Container
        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: #F5F5F7; border-radius: 10px; padding: 10px;")
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        # Fields
        self.code_edit = QLineEdit(self.user.code if self.user else "")
        self.code_edit.setPlaceholderText("唯一标识 ID")
        if self.mode == "edit":
            self.code_edit.setReadOnly(True) # Usually ID shouldn't change, or allow if DB supports it
            self.code_edit.setStyleSheet("color: #666; background-color: #E5E5E5;")
        else:
            self.code_edit.setStyleSheet("background-color: white;")
            
        self.name_edit = QLineEdit(self.user.name if self.user else "")
        self.name_edit.setPlaceholderText("姓名")
        self.name_edit.setStyleSheet("background-color: white;")
        
        self.position_edit = QLineEdit(self.user.position if self.user and self.user.position else "")
        self.position_edit.setPlaceholderText("职位 (选填)")
        self.position_edit.setStyleSheet("background-color: white;")
        
        self.contact_edit = QLineEdit(self.user.contact if self.user and self.user.contact else "")
        self.contact_edit.setPlaceholderText("值班电话 (选填)")
        self.contact_edit.setStyleSheet("background-color: white;")
        
        # Color Selection
        self.color = self.user.color if self.user and self.user.color else "#3498DB"
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(40, 40)
        self.btn_color.setCursor(Qt.PointingHandCursor)
        self.btn_color.clicked.connect(self.choose_color)
        self.update_color_btn()
        
        # Labels styling
        def style_label(text):
            l = QLabel(text)
            l.setStyleSheet("font-weight: 500; color: #333;")
            return l

        form_layout.addRow(style_label("ID (Code):"), self.code_edit)
        form_layout.addRow(style_label("姓名:"), self.name_edit)
        form_layout.addRow(style_label("职位:"), self.position_edit)
        form_layout.addRow(style_label("电话:"), self.contact_edit)
        form_layout.addRow(style_label("颜色:"), self.btn_color)
        
        layout.addWidget(form_widget)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()

        btn_delete = None
        if self.mode == "edit" and callable(self.on_delete):
            btn_delete = QPushButton("删除")
            btn_delete.setFixedSize(80, 36)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setStyleSheet("""
                QPushButton {
                    color: #FF3B30;
                    background-color: white;
                    border: 1px solid #E5E5EA;
                    border-radius: 18px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #FFF0F0;
                    border-color: #FF3B30;
                }
                QPushButton:pressed {
                    background-color: #FFD1D1;
                }
            """)

            def on_delete_clicked():
                name = self.user.name if self.user and self.user.name else ""
                code = self.user.code if self.user else ""
                label = f"{name}（{code}）" if name else code
                if QMessageBox.question(self, "确认删除", f"确定删除 {label}？") != QMessageBox.Yes:
                    return
                ok, msg = self.on_delete()
                if ok:
                    self.reject()
                else:
                    QMessageBox.warning(self, "删除失败", msg or "删除失败")

            btn_delete.clicked.connect(on_delete_clicked)

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(100, 36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F5F5F7;
                border-color: #C7C7CC;
            }
            QPushButton:pressed {
                background-color: #E5E5EA;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("保存" if self.mode == "edit" else "添加")
        btn_save.setFixedSize(100, 36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #007AFF; 
                color: white; 
                border-radius: 18px; 
                font-weight: bold;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #0062CC; }
            QPushButton:pressed { background-color: #0051A8; }
        """)
        btn_save.clicked.connect(self.accept)
        
        if btn_delete:
            btn_layout.addSpacing(10) # Move slightly right
            btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def update_color_btn(self):
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color};
                border: 3px solid white;
                border-radius: 20px;
                min-width: 40px;
                min-height: 40px;
            }}
            QPushButton:hover {{
                border: 3px solid #E5E5EA;
            }}
        """)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "选择颜色")
        if color.isValid():
            self.color = color.name()
            self.update_color_btn()

    def get_data(self):
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "position": self.position_edit.text().strip(),
            "contact": self.contact_edit.text().strip(),
            "color": self.color
        }

class SettingsView(QWidget):
    def __init__(self, users, db_manager: DBManager, main_window):
        super().__init__()
        self.users = users
        self.db_manager = db_manager
        self.main_window = main_window 
        self.rules = RulesManager.load_rules()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Content Area ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Page 1: Rules
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.stack.addWidget(self.tab_rules)
        
        # Page 2: Personnel
        self.tab_personnel = QWidget()
        self.init_personnel_tab()
        self.stack.addWidget(self.tab_personnel)
        
        # Init state
        self.switch_tab(0)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Scroll Area for modern long page feel ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(10, 10, 10, 30)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # --- Section 1: Weekly Rules (Cards) ---
        lbl_weekly = QLabel("每周排班规则")
        lbl_weekly.setStyleSheet("font-size: 22px; font-weight: bold; color: #1D1D1F;")
        content_layout.addWidget(lbl_weekly)
        
        lbl_weekly_desc = QLabel("点击卡片可配置当天的排班模式和人员。")
        lbl_weekly_desc.setStyleSheet("font-size: 14px; color: #86868B; margin-bottom: 10px;")
        content_layout.addWidget(lbl_weekly_desc)
        
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
        self.day_cards = []
        
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        for i, day_name in enumerate(weekdays):
            card = WeeklyRuleCard(i, day_name)
            card.clicked.connect(lambda idx=i: self.open_day_config(idx))
            self.day_cards.append(card)
            # 4 cards per row
            self.cards_layout.addWidget(card, i // 4, i % 4)
            
        content_layout.addLayout(self.cards_layout)
        
        # --- Section 2: Loop Settings (Start Date + Pool) ---
        content_layout.addSpacing(20)
        
        # Loop Start Date Container
        loop_date_container = QWidget()
        loop_date_layout = QHBoxLayout(loop_date_container)
        loop_date_layout.setContentsMargins(0, 0, 0, 0)
        loop_date_layout.setSpacing(10)
        
        lbl_pool = QLabel("循环池人员 (Loop Pool)")
        lbl_pool.setStyleSheet("font-size: 20px; font-weight: bold; color: #1D1D1F;")
        loop_date_layout.addWidget(lbl_pool)
        
        loop_date_layout.addSpacing(30)
        
        loop_date_icon = QLabel("🔄 循环起始日期:")
        loop_date_icon.setStyleSheet("font-size: 16px; color: #1D1D1F; font-weight: 500;")
        loop_date_layout.addWidget(loop_date_icon)
        
        self.date_edit_loop = QDateEdit()
        self.date_edit_loop.setFixedWidth(180)
        self.date_edit_loop.setDisplayFormat("yyyy年 MM月 dd日")
        self.date_edit_loop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        # Default 2026-01-05
        self.date_edit_loop.setDate(QDate(2026, 1, 5))
        self.date_edit_loop.setToolTip("点击修改循环起始日期")
        self.date_edit_loop.setStyleSheet("""
            QDateEdit {
                border: none;
                border-radius: 6px; 
                padding: 5px;
                color: #1D1D1F;
                background-color: #F5F5F7;
                font-size: 16px;
                font-weight: bold;
            }
            QDateEdit:hover { background-color: #E5E5EA; }
            QDateEdit:focus { background-color: #E5E5EA; color: #007AFF; }
        """)
        loop_date_layout.addWidget(self.date_edit_loop)
        
        loop_date_layout.addStretch()
        
        content_layout.addWidget(loop_date_container)
        
        # Loop Pool List
        pool_container = QFrame()
        pool_container.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #E5E5EA;")
        pool_inner_layout = QHBoxLayout(pool_container)
        pool_inner_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left: List
        self.list_pool = QListWidget()
        self.list_pool.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_pool.setSelectionMode(QAbstractItemView.ExtendedSelection) # Enable Multi-selection (Shift/Ctrl)
        self.list_pool.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_pool.customContextMenuRequested.connect(self.show_pool_context_menu)
        self.list_pool.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
            QListWidget::item {
                background-color: #F5F5F7;
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 4px;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #E5F1FB;
                color: #007AFF;
                border: 1px solid #007AFF; /* Highlight selection */
            }
        """)
        pool_inner_layout.addWidget(self.list_pool)
        
        # Right: Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        def create_tool_btn(text, icon, func, color=None):
            btn = QPushButton(f"{icon} {text}")
            style = """
                QPushButton {
                    text-align: left;
                    padding: 8px 15px;
                    border: 1px solid #E5E5EA;
                    border-radius: 8px;
                    background-color: white;
                    color: #333;
                }
                QPushButton:hover { background-color: #F5F5F7; }
            """
            if color == "red":
                style = """
                QPushButton {
                    text-align: left;
                    padding: 8px 15px;
                    border: 1px solid #FF3B30;
                    border-radius: 8px;
                    background-color: white;
                    color: #FF3B30;
                }
                QPushButton:hover { background-color: #FFF0F0; }
                """
            
            btn.setStyleSheet(style)
            btn.clicked.connect(func)
            return btn
            
        btn_layout.addWidget(create_tool_btn("选择人员添加", "👤", self.select_add_pool))
        
        # Move Up/Down buttons
        btn_layout.addWidget(create_tool_btn("上移", "⬆️", self.move_item_up))
        btn_layout.addWidget(create_tool_btn("下移", "⬇️", self.move_item_down))
        
        # Delete Button (New)
        btn_layout.addStretch() # Push delete to bottom or just below others? User box was at bottom of list height usually. 
        # Actually the red box in screenshot is just below "Down", there is space below.
        # But usually delete is separated or at bottom. 
        # The user's red box is immediately below "Down" button.
        # Let's add a small spacer then the delete button.
        btn_layout.addSpacing(10)
        btn_layout.addWidget(create_tool_btn("删除选中", "🗑️", self.remove_from_pool, color="red"))
        
        btn_layout.addStretch()
        pool_inner_layout.addLayout(btn_layout)
        
        content_layout.addWidget(pool_container)
        
        # --- Bottom: Save Action ---
        content_layout.addSpacing(20)
        btn_save = QPushButton("💾 保存所有配置")
        btn_save.setFixedHeight(45)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setProperty("class", "primary") # Uses QSS defined earlier
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #007AFF; 
                color: white; 
                font-weight: bold; 
                font-size: 16px; 
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover { background-color: #0062CC; }
        """)
        btn_save.clicked.connect(self.save_rules)
        content_layout.addWidget(btn_save)
        
        content_layout.addStretch()

        self.load_ui_from_rules()
    
    def open_day_config(self, day_index):
        day_conf = self.rules.get("days", {}).get(str(day_index), {})
        current_mode = day_conf.get("type", "loop")
        current_users = day_conf.get("users", [])
        day_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day_index]
        
        dlg = DayConfigDialog(day_name, current_mode, current_users, self.users, self)
        if dlg.exec_() == QDialog.Accepted:
            # Update internal rules immediately (in memory)
            if "days" not in self.rules: self.rules["days"] = {}
            
            self.rules["days"][str(day_index)] = {
                "type": dlg.mode,
                "users": dlg.selected_users
            }
            
            # Refresh UI
            self.load_ui_from_rules()

    # --- Replaced / Removed Old Methods ---
    # update_users_button_text -> Removed
    # on_mode_changed -> Removed
    # on_config_users_clicked -> Removed

    def create_action_btn(self, text, func, bg_color="#007AFF", text_color="white", border_color=None):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(func)
        style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
                border: {f'1px solid {border_color}' if border_color else 'none'};
            }}
            QPushButton:hover {{ opacity: 0.8; }}
        """
        btn.setStyleSheet(style)
        return btn

    def init_personnel_tab(self):
        layout = QVBoxLayout(self.tab_personnel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # --- Header Section ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索人员姓名或ID...")
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E5E5EA;
                border-radius: 20px;
                padding-left: 15px;
                padding-right: 15px;
                font-size: 14px;
                background-color: #F5F5F7;
            }
            QLineEdit:focus {
                border: 1px solid #007AFF;
                background-color: white;
            }
        """)
        self.search_input.textChanged.connect(self.load_users)
        header_layout.addWidget(self.search_input, 1) # Stretch factor 1
        
        # Add Button
        btn_add = self.create_action_btn("➕ 添加人员", self.add_user, "#5856D6")
        header_layout.addWidget(btn_add)
        
        # Import Button
        btn_import = self.create_action_btn("📥 Excel导入", self.import_from_excel, "#34C759")
        header_layout.addWidget(btn_import)
        
        layout.addLayout(header_layout)
        
        # --- Table Section ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "姓名", "职位", "电话", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(4, 90)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection) # Allow multiple selection (Shift/Ctrl)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        
        # Table Style
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E5EA;
                border-radius: 12px;
                background-color: white;
                gridline-color: #E5E5EA;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #F5F5F7;
            }
            QTableWidget::item:selected {
                background-color: #E5F1FB;
                color: #007AFF;
            }
            QHeaderView::section {
                background-color: #F5F5F7;
                padding: 12px;
                border: none;
                border-bottom: 1px solid #E5E5EA;
                font-weight: bold;
                color: #86868B;
            }
        """)
        
        layout.addWidget(self.table)
        
        self.load_users()

    def update_data(self, users):
        self.users = users
        self.load_users()
        self.load_ui_from_rules()

    def show_context_menu(self, pos):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        # Get selected rows (unique)
        rows = sorted(set(item.row() for item in selected_items))
        if not rows:
            return
            
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        
        # Win11 Style
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 6px;
                color: #333;
                font-size: 13px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #F2F2F7;
                color: #000;
            }
            QMenu::icon {
                padding-left: 10px;
            }
        """)
        
        # Delete Action
        action_del = QAction("删除选中人员", self)
        # Using a trash icon emoji for simplicity, or could load icon
        action_del.setText(f"🗑️ 删除 ({len(rows)})")
        action_del.triggered.connect(lambda: self.delete_selected_users(rows))
        menu.addAction(action_del)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def delete_selected_users(self, rows):
        # Gather user info
        users_to_delete = []
        names = []
        
        for row in rows:
            # Code is in column 0
            code_item = self.table.item(row, 0)
            if code_item:
                code = code_item.text()
                user = self._find_user(code)
                if user:
                    users_to_delete.append(user)
                    names.append(user.name)
        
        if not users_to_delete:
            return

        # Confirmation
        msg = f"确定要删除选中的 {len(users_to_delete)} 名人员吗？\n\n"
        if len(names) <= 5:
            msg += "、".join(names)
        else:
            msg += "、".join(names[:5]) + " 等..."
            
        reply = QMessageBox.question(self, "确认批量删除", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success_count = 0
            fail_count = 0
            
            for user in users_to_delete:
                ok = self.db_manager.delete_user(user.id)
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            
            # Reload
            self.main_window.reload_data()
            self.users = self.db_manager.get_all_users()
            self.load_users()
            
            if fail_count > 0:
                QMessageBox.warning(self, "完成", f"删除完成。\n成功: {success_count}\n失败: {fail_count}")
            else:
                QMessageBox.information(self, "成功", f"成功删除 {success_count} 名人员。")

    # --- Logic for Rules Tab ---
    
    def load_ui_from_rules(self):
        days = self.rules.get("days", {})
        
        # Update Cards
        for i, card in enumerate(self.day_cards):
            d_conf = days.get(str(i), {})
            mode = d_conf.get("type", "loop")
            users = d_conf.get("users", [])
            card.update_state(mode, users, self._find_user)

        # Set Rotation Date (Hidden but maintained)
        # rot_date_str = self.rules.get("rotation_start_date", "2026-01-09")
        # self.date_edit_rotation.setDate(QDate.fromString(rot_date_str, "yyyy-MM-dd"))
        
        # Set Loop Start Date
        loop_start_str = self.rules.get("loop_start_date", "2026-01-05")
        self.date_edit_loop.setDate(QDate.fromString(loop_start_str, "yyyy-MM-dd"))

        # Set Pool
        pool = self.rules.get("loop_pool", [])
        self.list_pool.clear()
        for code in pool:
            user = self._find_user(code)
            name = user.name if user else "未知"
            item = QListWidgetItem(f"{name} ({code})")
            item.setData(Qt.UserRole, code)
            self.list_pool.addItem(item)

    def add_all_to_pool(self):
        existing_codes = {self.list_pool.item(i).data(Qt.UserRole) for i in range(self.list_pool.count())}
        for user in self.users:
            if user.code not in existing_codes:
                item = QListWidgetItem(f"{user.name} ({user.code})")
                item.setData(Qt.UserRole, user.code)
                self.list_pool.addItem(item)

    def select_add_pool(self):
        dialog = UserSelectionDialog(self.users, [], self, "添加人员到循环池")
        if dialog.exec_():
            selected = dialog.get_selected_codes()
            existing_codes = {self.list_pool.item(i).data(Qt.UserRole) for i in range(self.list_pool.count())}
            for code in selected:
                if code not in existing_codes:
                    user = self._find_user(code)
                    name = user.name if user else "未知"
                    item = QListWidgetItem(f"{name} ({code})")
                    item.setData(Qt.UserRole, code)
                    self.list_pool.addItem(item)

    def show_pool_context_menu(self, pos):
        selected_items = self.list_pool.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        
        # Win11 Style Menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 6px;
                color: #333;
                font-size: 13px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #F2F2F7;
                color: #000;
            }
        """)
        
        action_del = QAction(f"🗑️ 删除选中 ({len(selected_items)})", self)
        action_del.triggered.connect(self.remove_from_pool)
        menu.addAction(action_del)
        
        menu.exec_(self.list_pool.viewport().mapToGlobal(pos))

    def remove_from_pool(self):
        for item in self.list_pool.selectedItems():
            self.list_pool.takeItem(self.list_pool.row(item))

    def move_item_up(self):
        row = self.list_pool.currentRow()
        if row > 0:
            item = self.list_pool.takeItem(row)
            self.list_pool.insertItem(row - 1, item)
            self.list_pool.setCurrentRow(row - 1)

    def move_item_down(self):
        row = self.list_pool.currentRow()
        if row >= 0 and row < self.list_pool.count() - 1:
            item = self.list_pool.takeItem(row)
            self.list_pool.insertItem(row + 1, item)
            self.list_pool.setCurrentRow(row + 1)

    def reset_pool_index(self):
        RulesManager.save_state({"loop_index": 0})
        QMessageBox.information(self, "重置成功", "循环进度已重置为 0 (从列表第一人开始)")

    def save_rules(self):
        # Rules are already updated in self.rules["days"] via open_day_config
        # We just need to ensure rotation date and pool are synced
        
        rules = self.rules
        if "days" not in rules: rules["days"] = {}
        
        # Rotation Date (Internal Default)
        # Ensure it exists, default to 2026-01-09 if not set, or keep existing
        if "rotation_start_date" not in rules:
             rules["rotation_start_date"] = "2026-01-09"
        
        # Loop Start Date
        rules["loop_start_date"] = self.date_edit_loop.date().toString("yyyy-MM-dd")
        
        # Loop Pool
        pool = []
        for i in range(self.list_pool.count()):
            pool.append(self.list_pool.item(i).data(Qt.UserRole))
        rules["loop_pool"] = pool
        
        try:
            RulesManager.save_rules(rules)
            QMessageBox.information(self, "保存成功", "排班规则已成功保存！")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存规则时出错: {str(e)}")

    def _find_user(self, code):
        for u in self.users:
            if u.code == code: return u
        return None

    # --- Logic for Personnel Tab (Legacy Helper) ---
    def load_users(self):
        search = self.search_input.text().lower()
        self.table.setRowCount(0)
        
        for user in self.users:
            if search and search not in user.name.lower() and search not in user.code.lower():
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Helper to create centered item
            def create_item(text):
                item = QTableWidgetItem(str(text) if text else "")
                item.setTextAlignment(Qt.AlignCenter)
                return item
            
            self.table.setItem(row, 0, create_item(user.code))
            self.table.setItem(row, 1, create_item(user.name))
            self.table.setItem(row, 2, create_item(user.position))
            self.table.setItem(row, 3, create_item(user.contact))
            
            btn_edit = QPushButton("编辑")
            btn_edit.setFixedSize(60, 28)
            btn_edit.setFlat(True)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    color: #007AFF;
                    background-color: transparent;
                    border: none;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #E5F1FB;
                    border-radius: 8px;
                }
            """)
            btn_edit.clicked.connect(lambda _, u=user: self.edit_user(u))
            
            widget = QWidget()
            v_layout = QVBoxLayout(widget)
            v_layout.setContentsMargins(0, 0, 0, 0)
            v_layout.setAlignment(Qt.AlignCenter)
            v_layout.setSpacing(0)
            v_layout.addWidget(btn_edit)
            
            self.table.setCellWidget(row, 4, widget)
            self.table.setRowHeight(row, 44)

    def add_user(self):
        dialog = UserDialog(parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            code = data["code"]
            name = data["name"]
            position = data["position"]
            contact = data["contact"]
            color = data["color"]
            
            if not code:
                QMessageBox.warning(self, "错误", "ID不能为空")
                return

            try:
                # Returns (user_obj, message)
                new_user, msg = self.db_manager.add_user(code, name=name, position=position, contact=contact, color=color)
                if new_user:
                    self.main_window.reload_data()
                    self.users = self.db_manager.get_all_users()
                    self.load_users()
                    QMessageBox.information(self, "成功", "添加成功")
                else:
                    QMessageBox.warning(self, "错误", f"添加失败: {msg}")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def edit_user(self, user):
        dialog = UserDialog(user, self, on_delete=lambda u=user: self._delete_user(u, confirm=False))
        if dialog.exec_():
            data = dialog.get_data()
            success, msg = self.db_manager.update_user(
                user.id,
                code=data["code"],
                name=data["name"],
                position=data["position"],
                contact=data["contact"],
                color=data["color"]
            )
            if success:
                self.main_window.reload_data()
                self.users = self.db_manager.get_all_users()
                self.load_users()
            else:
                QMessageBox.warning(self, "错误", f"更新失败: {msg}")

    def _delete_user(self, user, confirm=True):
        name = user.name if user and user.name else ""
        code = user.code if user else ""
        label = f"{name}（{code}）" if name else code
        if confirm and QMessageBox.question(self, "确认删除", f"确定删除 {label}？") != QMessageBox.Yes:
            return False, "已取消"

        ok = self.db_manager.delete_user(user.id)
        if not ok:
            return False, "删除失败"

        self.main_window.reload_data()
        self.users = self.db_manager.get_all_users()
        self.load_users()
        return True, ""

    def delete_user(self, user):
        self._delete_user(user, confirm=True)
            
    def import_from_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择人员信息Excel文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if not file_path:
            return

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            
            added_count = 0
            updated_count = 0
            
            # Start from row 3 (index 2)
            # Columns based on analysis: 
            # Row 2 headers: '序号', '姓名', '性别', '政治面貌', '班 组', '职号', '职务'
            # Index:          0       1       2       3           4        5       6
            
            progress = QProgressDialog("正在导入人员数据...", "取消", 0, sheet.max_row, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Palette for auto-assigning colors
            colors = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD",
                "#D4A5A5", "#9B59B6", "#3498DB", "#F1C40F", "#E67E22",
                "#2ECC71", "#1ABC9C", "#34495E", "#16A085", "#27AE60",
                "#2980B9", "#8E44AD", "#2C3E50", "#F39C12", "#D35400",
                "#C0392B", "#BDC3C7", "#7F8C8D"
            ]

            for i, row in enumerate(sheet.iter_rows(min_row=3, values_only=True)):
                if progress.wasCanceled():
                    break
                progress.setValue(i + 3)
                
                if not row or not row[1]: # Skip empty name
                    continue
                    
                name = str(row[1]).strip()
                
                # Generate ID automatically: A, B, C...
                if i < 26:
                    code = chr(65 + i)
                else:
                    code = chr(65 + (i // 26) - 1) + chr(65 + (i % 26))
                    
                position = str(row[6]).strip() if row[6] else ""
                contact = str(row[7]).strip() if row[7] else ""
                
                # Auto-assign color
                color = colors[i % len(colors)]

                # Check existence
                user = self._find_user(code)
                if user:
                    # Update (preserve existing color if desired, but user asked for different colors on import)
                    # We will update color only if it's currently default or empty, OR just update it to ensure distribution
                    # Let's update it to ensure the requested "different colors" logic is applied.
                    self.db_manager.update_user(user.id, name=name, position=position, contact=contact, color=color)
                    updated_count += 1
                else:
                    # Add
                    self.db_manager.add_user(code, name=name, position=position, contact=contact, color=color)
                    added_count += 1
            
            progress.setValue(sheet.max_row)
            
            # Reload
            self.main_window.reload_data()
            self.users = self.db_manager.get_all_users()
            self.load_users()
            
            QMessageBox.information(self, "导入成功", f"导入完成！\n新增: {added_count} 人\n更新: {updated_count} 人")
            
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"发生错误: {str(e)}")
