import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QAction, QSplitter, QMessageBox, QToolBar, QLabel,
                             QProgressDialog, QFileDialog, QStackedWidget, QFrame, QPushButton, QMenu)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QIcon, QFont

from src.db_manager import DBManager
from src.scheduler import Scheduler
from src.staff_panel import StaffPanel
from src.calendar_view import CalendarView
from src.stats_view import StatsView
from src.settings_view import SettingsView
from src.system_settings import SystemSettingsDialog
from src.exporter import Exporter
from src.models import Schedule

class SchedulerWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    warning = pyqtSignal(str)

    def __init__(self, users, history_counts, last_duty_dates, existing_schedules, target_week_starts, initial_last_weekend_duty=None, weekend_history_counts=None, mode="all"):
        super().__init__()
        self.users = users
        self.history_counts = history_counts
        self.last_duty_dates = last_duty_dates
        self.existing_schedules = existing_schedules
        self.target_week_starts = target_week_starts
        self.initial_last_weekend_duty = initial_last_weekend_duty or {}
        self.weekend_history_counts = weekend_history_counts or {}
        self.mode = mode

    def run(self):
        try:
            import datetime
            from src.scheduler import Scheduler
            from src.rules_manager import RulesManager
            
            all_new_schedules = []
            
            # Load initial loop state
            state = RulesManager.load_state()
            current_loop_index = state.get("loop_index", 0)
            
            # Load rules once
            rules = RulesManager.load_rules()
            
            warnings = []
            
            # 遍历指定的所有周起始日期
            for week_start in self.target_week_starts:
                # Filter existing schedules for this week
                week_end = week_start + datetime.timedelta(days=7)
                week_existing = [
                    s for s in self.existing_schedules 
                    if week_start <= s.date < week_end
                ]
                
                # Init Scheduler with new signature
                scheduler = Scheduler(self.users, week_start, loop_index=current_loop_index, rules=rules)
                week_new_schedules = scheduler.generate_schedule(week_existing, mode=self.mode)
                
                all_new_schedules.extend(week_new_schedules)
                
                # Update loop index for next week
                current_loop_index = scheduler.new_loop_index

            # Save final state
            RulesManager.save_state({"loop_index": current_loop_index})

            if warnings:
                self.warning.emit("\n\n".join(warnings))

            self.finished.emit(all_new_schedules)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class SidebarButton(QPushButton):
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self.setFont(QFont("Microsoft YaHei", 10))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能排班系统 V2.0.0")
        self.resize(1400, 900)
        
        # Set Window Icon
        import os
        if os.path.exists("resources/icon.png"):
            self.setWindowIcon(QIcon("resources/icon.png"))
        
        # Init DB
        self.db_manager = DBManager()
        self.users = self.db_manager.get_all_users()
        self.schedules = self.db_manager.get_all_schedules()
        
        # Link user objects to schedules
        self._bind_users_to_schedules()

        self.init_ui()
        
        # Connect signals
        self.calendar_view.user_dropped.connect(self.handle_manual_drop)
        self.calendar_view.user_removed.connect(self.handle_user_removed)
        self.calendar_view.day_cleared.connect(self.handle_day_cleared)

    def _bind_users_to_schedules(self):
        user_map = {u.id: u for u in self.users}
        for s in self.schedules:
            if s.user_id in user_map:
                s.user = user_map[s.user_id]

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main vertical layout (Header + Body)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- 1. Top Header ---
        self.init_header()
        
        # --- 2. Body Area (Sidebar + Content) ---
        self.body_widget = QWidget()
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.body_widget)

        # --- Left Sidebar (Contextual) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("""
            #Sidebar {
                background-color: #F5F5F7;
                border-right: 1px solid #E5E5E5;
            }
        """)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 20, 15, 20)
        self.sidebar_layout.setSpacing(15)
        
        # App Title in Sidebar (with Settings Button)
        sidebar_header = QHBoxLayout()
        
        title_label = QLabel("智能排班")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        sidebar_header.addWidget(title_label)
        
        sidebar_header.addStretch()
        
        self.btn_sys_settings = QPushButton("⚙️")
        self.btn_sys_settings.setFixedSize(32, 32)
        self.btn_sys_settings.setCursor(Qt.PointingHandCursor)
        self.btn_sys_settings.setToolTip("系统设置")
        self.btn_sys_settings.clicked.connect(self.open_system_settings)
        self.btn_sys_settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: #888;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #E5E5E5;
                color: #333;
            }
        """)
        sidebar_header.addWidget(self.btn_sys_settings)
        
        self.sidebar_layout.addLayout(sidebar_header)
        
        # "Schedule Overview" Indicator
        self.btn_nav_schedule = QPushButton("📅  排班概览")
        self.btn_nav_schedule.setCheckable(True)
        self.btn_nav_schedule.setChecked(True)
        self.btn_nav_schedule.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 15px;
                border: none;
                border-radius: 8px;
                color: white;
                background-color: #007AFF;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.sidebar_layout.addWidget(self.btn_nav_schedule)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        self.sidebar_layout.addWidget(line)
        
        # Staff Panel (Embedded in Sidebar)
        self.staff_panel = StaffPanel(self.users, self.db_manager, self.reload_data)
        self.sidebar_layout.addWidget(self.staff_panel)
        
        self.body_layout.addWidget(self.sidebar)

        # --- Main Content Area ---
        self.stacked_widget = QStackedWidget()
        self.body_layout.addWidget(self.stacked_widget)

        # Page 0: Schedule View (Only Calendar now)
        self.page_schedule = QWidget()
        self.init_schedule_page()
        self.stacked_widget.addWidget(self.page_schedule)

        # Page 1: Settings View
        self.settings_view = SettingsView(self.users, self.db_manager, self)
        self.stacked_widget.addWidget(self.settings_view)

        # Page 2: Stats View
        self.stats_view = StatsView(self.users, self.schedules)
        self.stacked_widget.addWidget(self.stats_view)
        
    def init_header(self):
        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet("background-color: white; border-bottom: 1px solid #E5E5E5;")
        
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Title
        lbl_title = QLabel("排班工作台")
        lbl_title.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(lbl_title)
        
        layout.addStretch()
        
        # --- Schedule Actions (Auto, Clear, Export) ---
        self.action_container = QWidget()
        action_layout = QHBoxLayout(self.action_container)
        action_layout.setContentsMargins(0,0,0,0)
        action_layout.setSpacing(10)
        
        def create_action_btn(text, func, bg_color="#007AFF", text_color="white", border_color=None):
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

        # New Buttons: Year Schedule, Month Schedule
        self.btn_year_schedule = create_action_btn("📅 一键本年排班", self.on_schedule_year_clicked, "#5856D6")
        self.btn_year_schedule.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_year_schedule.customContextMenuRequested.connect(self.show_year_context_menu)
        action_layout.addWidget(self.btn_year_schedule)
        
        self.btn_month_schedule = create_action_btn("🗓️ 一键本月排班", self.on_schedule_month_clicked, "#007AFF")
        self.btn_month_schedule.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_month_schedule.customContextMenuRequested.connect(self.show_month_context_menu)
        action_layout.addWidget(self.btn_month_schedule)
        
        self.btn_export = create_action_btn("📤 导出Excel", self.export_schedule, "#34C759")
        action_layout.addWidget(self.btn_export)
        
        layout.addWidget(self.action_container)

        # --- Settings Context Actions (Rules, Personnel) ---
        self.settings_action_container = QWidget()
        settings_action_layout = QHBoxLayout(self.settings_action_container)
        settings_action_layout.setContentsMargins(0, 0, 0, 0)
        settings_action_layout.setSpacing(10)
        
        def create_tab_btn(text, icon, tab_index, active_color="#007AFF"):
            btn = QPushButton(f"{icon} {text}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda: self.switch_settings_tab(tab_index))
            style = f"""
                QPushButton {{
                    background-color: #F5F5F7;
                    color: #555;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    margin-left: 10px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #E5E5E5; }}
                QPushButton:checked {{ 
                    background-color: {active_color}; 
                    color: white; 
                    font-weight: bold; 
                }}
            """
            btn.setStyleSheet(style)
            return btn
            
        self.btn_tab_rules = create_tab_btn("排班规则", "⚙️", 0, "#007AFF")
        self.btn_tab_personnel = create_tab_btn("人员管理", "👥", 1, "#5856D6")
        self.btn_tab_rules.setChecked(True) # Default
        
        settings_action_layout.addWidget(self.btn_tab_rules)
        settings_action_layout.addWidget(self.btn_tab_personnel)
        
        layout.addWidget(self.settings_action_container)
        self.settings_action_container.hide() # Hidden by default
        
        # Vertical Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        line.setFixedHeight(24)
        layout.addWidget(line, 0, Qt.AlignVCenter)
        
        # --- Global Navigation (Stats, Settings) ---
        # Styled as top-right buttons
        def create_nav_btn(text, icon, view_index):
            btn = QPushButton(f"{icon} {text}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda: self.switch_view(view_index))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F7;
                    color: #555;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    margin-left: 10px;
                }
                QPushButton:hover { background-color: #E5E5E5; }
                QPushButton:checked { background-color: #E0E0E0; color: #333; font-weight: bold; }
            """)
            return btn
            
        self.btn_top_schedule = create_nav_btn("排班概览", "📅", 0)
        layout.addWidget(self.btn_top_schedule)

        self.btn_top_stats = create_nav_btn("统计报表", "📊", 2)
        layout.addWidget(self.btn_top_stats)
        
        self.btn_top_settings = create_nav_btn("人员管理", "⚙️", 1)
        layout.addWidget(self.btn_top_settings)
        
        self.main_layout.addWidget(self.header)

    def init_schedule_page(self):
        layout = QVBoxLayout(self.page_schedule)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Center: Calendar (Takes full space now)
        self.calendar_view = CalendarView()
        self.calendar_view.update_schedule(self.schedules)
        layout.addWidget(self.calendar_view)

    def switch_view(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
        # Update Nav Buttons State
        self.btn_top_schedule.setChecked(index == 0)
        self.btn_top_settings.setChecked(index == 1)
        self.btn_top_stats.setChecked(index == 2)
            
        # Contextual UI changes
        if index == 0: # Schedule View
            self.sidebar.setVisible(True)
            self.action_container.setVisible(True)
            self.settings_action_container.setVisible(False)
            self.reload_data() # Refresh calendar
        else: # Settings or Stats
            self.sidebar.setVisible(False) # Maximize space for settings/stats
            self.action_container.setVisible(False) # Hide schedule actions
            
            if index == 1:
                self.settings_action_container.setVisible(True)
                self.settings_view.load_users()
            elif index == 2:
                self.settings_action_container.setVisible(False)
                self.stats_view.update_data(self.schedules, self.users)

    def switch_settings_tab(self, tab_index):
        if hasattr(self, 'settings_view'):
            self.settings_view.switch_tab(tab_index)
            # Ensure buttons state
            self.btn_tab_rules.setChecked(tab_index == 0)
            self.btn_tab_personnel.setChecked(tab_index == 1)

    # --- Legacy Redirects (for compatibility if needed) ---
    def toggle_settings_view(self):
        self.switch_view(1)
        
    def toggle_stats_view(self):
        self.switch_view(2)

    def open_system_settings(self):
        dialog = SystemSettingsDialog(self)
        dialog.exec_()

    def _get_mondays_of_month(self, year, month):
        """获取某月所有周的周一（包括跨月显示的周）"""
        import calendar
        c = calendar.Calendar(firstweekday=calendar.MONDAY)
        mondays = []
        for date in c.itermonthdates(year, month):
            # 只要是周一，且在当前视图范围内（itermonthdates会自动包含首尾的跨月周），就加入
            # 这样可以解决"上个月未满周月，本月补齐"的需求
            if date.weekday() == 0:
                mondays.append(date)
        return mondays

    def _get_mondays_of_year(self, year):
        """
        获取某年所有周的周一。
        规则：如果这一周的某一天属于本年，那么在排列本年的时候，这一周的其它天也要排列。
        即：只要周内任意一天在今年内，该周（周一）就应该被包含。
        """
        mondays = []
        import datetime
        
        # 1. 从1月1日开始
        d = datetime.date(year, 1, 1)
        
        # 2. 找到包含1月1日的那一周的周一
        # 如果1月1日是周一，则是当天；如果是周二，则是前一天，依此类推
        start_monday = d - datetime.timedelta(days=d.weekday())
        
        current_monday = start_monday
        
        # 3. 只要周一开始日期还在本年（或之前），就继续检查
        # 实际上，只要 current_monday 的年份 <= year，说明这一周至少有一部分（或者全部）
        # 属于本年（或者这一周包含了本年的开始部分）。
        # 如果 current_monday 到了下一年的1月X日，那么这一周肯定全都在下一年了（因为周一是一周第一天），
        # 就不需要包含了。
        while current_monday.year <= year:
            mondays.append(current_monday)
            current_monday += datetime.timedelta(weeks=1)
            
        return mondays

    def on_schedule_year_clicked(self):
        year = self.calendar_view.current_date.year
        mondays = self._get_mondays_of_year(year)
        self.auto_schedule_range(mondays, f"{year}年全年")

    def on_schedule_month_clicked(self):
        year = self.calendar_view.current_date.year
        month = self.calendar_view.current_date.month
        mondays = self._get_mondays_of_month(year, month)
        
        # Ask for mode
        # msg = QMessageBox(self)
        # msg.setWindowTitle("选择排班模式")
        # msg.setText(f"即将进行 {year}年{month}月 排班。\n请选择操作方式：")
        # msg.setIcon(QMessageBox.Question)
        
        # btn_all = msg.addButton("一键完整排班", QMessageBox.ActionRole)
        # btn_l1 = msg.addButton("第1步：仅排一级人员", QMessageBox.ActionRole)
        # btn_fill = msg.addButton("第2步：补齐剩余人员", QMessageBox.ActionRole)
        # msg.addButton("取消", QMessageBox.RejectRole)
        
        # self._apply_msg_style(msg)
        # msg.exec_()
        
        # clicked_button = msg.clickedButton()
        # if clicked_button == btn_all:
        #     self.auto_schedule_range(mondays, f"{year}年{month}月 (完整)", mode="all")
        # elif clicked_button == btn_l1:
        #     self.auto_schedule_range(mondays, f"{year}年{month}月 (仅一级)", mode="level1_only")
        # elif clicked_button == btn_fill:
        #     self.auto_schedule_range(mondays, f"{year}年{month}月 (补齐)", mode="fill_rest")

        # Simplify to One-Click Full Schedule
        self.auto_schedule_range(mondays, f"{year}年{month}月", mode="all")

    def show_year_context_menu(self, pos):
        menu = QMenu(self)
        action_clear = QAction("清除本年排班", self)
        action_clear.triggered.connect(self.clear_year_schedule)
        menu.addAction(action_clear)
        menu.exec_(self.btn_year_schedule.mapToGlobal(pos))

    def show_month_context_menu(self, pos):
        menu = QMenu(self)
        action_clear = QAction("清除本月排班", self)
        action_clear.triggered.connect(self.clear_month_schedule)
        menu.addAction(action_clear)
        menu.exec_(self.btn_month_schedule.mapToGlobal(pos))

    def clear_year_schedule(self):
        year = self.calendar_view.current_date.year
        reply = self.show_custom_confirmation("确认清除", f"确定要清除 {year} 年全年的排班数据吗？\n注意：这将清除该年所有周一对应的整周排班。")
        if reply == QMessageBox.Yes:
            mondays = self._get_mondays_of_year(year)
            if not mondays:
                return
            start_date = mondays[0]
            end_date = mondays[-1] + datetime.timedelta(days=6)
            self.db_manager.clear_range_schedules(start_date, end_date, keep_locked=False)
            self.reload_data()
            self.show_custom_message("成功", "本年排班已清除", QMessageBox.Information)

    def clear_month_schedule(self):
        year = self.calendar_view.current_date.year
        month = self.calendar_view.current_date.month
        reply = self.show_custom_confirmation("确认清除", f"确定要清除 {year}年{month}月 的排班数据吗？")
        if reply == QMessageBox.Yes:
            mondays = self._get_mondays_of_month(year, month)
            if not mondays:
                return
            start_date = mondays[0]
            end_date = mondays[-1] + datetime.timedelta(days=6)
            self.db_manager.clear_range_schedules(start_date, end_date, keep_locked=False)
            self.reload_data()
            self.show_custom_message("成功", "本月排班已清除", QMessageBox.Information)

    def auto_schedule_range(self, target_week_starts, label_text, mode="all"):
        if not self.users:
            reply = QMessageBox.warning(self, "提示", "当前人员列表为空，请前往录入。", QMessageBox.Ok)
            if reply == QMessageBox.Ok:
                self.switch_view(1)  # 跳转到人员管理界面
            return

        if not target_week_starts:
            QMessageBox.warning(self, "提示", "所选时间范围内没有需要排班的周。")
            return

        # Get history counts & last duty dates for advanced rules
        history_counts = self.db_manager.get_history_counts()
        last_duty_dates = self.db_manager.get_last_duty_dates()
        weekend_history_counts = self.db_manager.get_weekend_history_counts()
        
        # Get Last Weekend Duty Status (for first week)
        initial_last_weekend_duty = {}
        if target_week_starts:
             # Logic: Previous Weekend relative to First Target Week
             # First Target Week Start is a Monday.
             # Previous Weekend is [Mon-2 days (Sat), Mon-1 day (Sun)]
             start_monday = target_week_starts[0]
             prev_sat = start_monday - datetime.timedelta(days=2)
             prev_sun = start_monday - datetime.timedelta(days=1)
             
             weekend_users = self.db_manager.get_users_on_duty_between(prev_sat, prev_sun)
             for u_code in weekend_users:
                 initial_last_weekend_duty[u_code] = True
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog(f"正在生成排班方案 ({label_text})...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None) 
        self.progress_dialog.show()

        # Start worker thread
        self.worker = SchedulerWorker(self.users, history_counts, last_duty_dates, self.schedules, target_week_starts, initial_last_weekend_duty, weekend_history_counts, mode=mode)
        self.worker.finished.connect(self.on_schedule_finished)
        self.worker.error.connect(self.on_schedule_error)
        self.worker.warning.connect(self.on_schedule_warning)
        self.worker.start()

    def on_schedule_warning(self, msg):
        self.show_custom_message("排班警告", msg, QMessageBox.Warning)

    def on_schedule_finished(self, new_schedules):
        self.progress_dialog.close()
        
        if not new_schedules:
            # 如果完全没有生成排班，提示用户
            # 但也有可能只是部分周生成了，这里 new_schedules 包含了所有生成的
            QMessageBox.warning(self, "排班结果", "未能生成排班方案，或者生成结果为空。请检查人员约束条件。")
            return

        try:
            # Use atomic replacement to avoid DB locks and ensure consistency
            self.db_manager.replace_schedules(new_schedules)
            
            # Refresh Memory
            self.reload_data()
            self.show_custom_message("成功", "排班完成！", QMessageBox.Information)
            
        except Exception as e:
            self.show_custom_message("错误", f"保存排班数据时出错: {str(e)}", QMessageBox.Critical)

    def on_schedule_error(self, error_msg):
        self.progress_dialog.close()
        self.show_custom_message("错误", f"排班算法出错: {error_msg}", QMessageBox.Critical)

    def show_custom_message(self, title, text, icon_type):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon_type)
        self._apply_msg_style(msg)
        msg.exec_()

    def show_custom_confirmation(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        self._apply_msg_style(msg)
        return msg.exec_()

    def _apply_msg_style(self, msg_box):
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                min-width: 260px;
            }
            QLabel {
                font-size: 14px;
                color: #333;
                padding: 10px;
            }
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 12px;
                min-width: 70px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #0051A8;
            }
        """)

    def export_schedule(self):
        # 1. Generate default filename based on current view
        year = self.calendar_view.current_date.year
        month = self.calendar_view.current_date.month
        default_filename = f"{year}年{month}月排班表.xls"

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出Excel", 
            default_filename,  # Set default filename
            "Excel Files (*.xls)"
        )
        
        if file_path:
            try:
                # Filter schedules strictly for the selected month
                target_schedules = [
                    s for s in self.schedules 
                    if s.date.year == year and s.date.month == month
                ]
                
                # Sort by ID to ensure deterministic order for same-day shifts
                target_schedules.sort(key=lambda s: s.id if s.id else 0)
                
                exporter = Exporter(target_schedules, self.users)
                # Pass year and month for title generation
                exporter.export_to_excel(file_path, year=year, month=month)
                
                self.show_custom_message("成功", f"排班表已导出到:\n{file_path}", QMessageBox.Information)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.show_custom_message("导出失败", str(e), QMessageBox.Critical)

    def handle_manual_drop(self, date, user_id, user_code, source_date=None):
        # Callback from CalendarView when a user is dropped
        try:
            # 1. Handle Move (if source_date is provided)
            if source_date:
                self.db_manager.delete_schedule(source_date, user_id)
            
            # 2. Add to target date
            # add_schedule handles existence check internally
            self.db_manager.add_schedule(date, user_id, is_locked=True)
            
            self.reload_data()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新排班失败: {str(e)}")

    def handle_user_removed(self, date, user_id):
        try:
            self.db_manager.delete_schedule(date, user_id)
            self.reload_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除人员失败: {str(e)}")

    def handle_day_cleared(self, date):
        try:
            self.db_manager.delete_day_schedule(date)
            self.reload_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"清除排班失败: {str(e)}")

    def reload_data(self):
        self.users = self.db_manager.get_all_users()
        self.schedules = self.db_manager.get_all_schedules()
        self._bind_users_to_schedules()
        
        # Update Views
        self.staff_panel.refresh_list(self.users)
        self.calendar_view.update_schedule(self.schedules)
        self.settings_view.update_data(self.users)
        # Settings and Stats update on view switch or manually
        if self.stacked_widget.currentIndex() == 2:
             self.stats_view.update_data(self.schedules, self.users)
