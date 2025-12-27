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

    def __init__(self, users, history_counts, last_duty_dates, existing_schedules, target_week_starts):
        super().__init__()
        self.users = users
        self.history_counts = history_counts
        self.last_duty_dates = last_duty_dates
        self.existing_schedules = existing_schedules
        self.target_week_starts = target_week_starts

    def run(self):
        try:
            import datetime
            from src.scheduler import Scheduler
            
            all_new_schedules = []
            current_history = self.history_counts.copy()
            current_last_duty = self.last_duty_dates.copy()
            warnings = []
            
            # 遍历指定的所有周起始日期
            for week_start in self.target_week_starts:
                # Filter existing schedules for this week
                week_end = week_start + datetime.timedelta(days=7)
                week_existing = [
                    s for s in self.existing_schedules 
                    if week_start <= s.date < week_end
                ]
                
                scheduler = Scheduler(self.users, week_start, current_history, current_last_duty)
                week_new_schedules = scheduler.generate_schedule(week_existing)
                
                if scheduler.last_error:
                    warnings.append(f"周起始 {week_start}:\n{scheduler.last_error}")

                if not week_new_schedules and scheduler.last_error:
                    # Failed completely for this week
                    continue

                all_new_schedules.extend(week_new_schedules)
                
                # Update history for next iteration
                for s in week_new_schedules:
                    current_history[s.user.code] = current_history.get(s.user.code, 0) + 1
                    current_last_duty[s.user.code] = s.date

            if warnings:
                self.warning.emit("\n\n".join(warnings))

            self.finished.emit(all_new_schedules)
            
        except Exception as e:
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
        self.setWindowTitle("智能排班系统 V1.0.0")
        self.resize(1400, 900)
        
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
        self.staff_panel = StaffPanel(self.users)
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
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
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
        
        # Vertical Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        line.setFixedHeight(24)
        layout.addWidget(line)
        
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
            self.reload_data() # Refresh calendar
        else: # Settings or Stats
            self.sidebar.setVisible(False) # Maximize space for settings/stats
            self.action_container.setVisible(False) # Hide schedule actions
            
            if index == 1:
                self.settings_view.load_users()
            elif index == 2:
                self.stats_view.update_data(self.schedules, self.users)

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
        """获取某年所有周的周一（只要该周的周一在该年内）"""
        mondays = []
        import datetime
        d = datetime.date(year, 1, 1)
        # Find first Monday of the year
        while d.weekday() != 0:
            d += datetime.timedelta(days=1)
        
        while d.year == year:
            mondays.append(d)
            d += datetime.timedelta(weeks=1)
        return mondays

    def on_schedule_year_clicked(self):
        year = self.calendar_view.current_date.year
        mondays = self._get_mondays_of_year(year)
        self.auto_schedule_range(mondays, f"{year}年全年")

    def on_schedule_month_clicked(self):
        year = self.calendar_view.current_date.year
        month = self.calendar_view.current_date.month
        mondays = self._get_mondays_of_month(year, month)
        self.auto_schedule_range(mondays, f"{year}年{month}月")

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
            self.db_manager.clear_range_schedules(start_date, end_date)
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
            self.db_manager.clear_range_schedules(start_date, end_date)
            self.reload_data()
            self.show_custom_message("成功", "本月排班已清除", QMessageBox.Information)

    def auto_schedule_range(self, target_week_starts, label_text):
        if not target_week_starts:
            QMessageBox.warning(self, "提示", "所选时间范围内没有需要排班的周。")
            return

        # Get history counts & last duty dates for advanced rules
        history_counts = self.db_manager.get_history_counts()
        last_duty_dates = self.db_manager.get_last_duty_dates()
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog(f"正在生成排班方案 ({label_text})...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None) 
        self.progress_dialog.show()

        # Start worker thread
        self.worker = SchedulerWorker(self.users, history_counts, last_duty_dates, self.schedules, target_week_starts)
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
            # Save to DB
            session = self.db_manager.get_session()
            
            # Use delete logic based on generated schedules range
            # Find min and max date in new_schedules to define range
            if new_schedules:
                min_date = min(s.date for s in new_schedules)
                max_date = max(s.date for s in new_schedules)
                
                # Delete existing within this exact range (day by day? or range?)
                # To be safe and consistent with "overwrite", we delete in range
                # But wait, new_schedules might have gaps if some weeks failed?
                # Actually, our scheduler generates continuous weeks if successful.
                # But to be safe, let's delete only for the weeks we scheduled.
                
                # Better approach: 
                # For each week start in our target list, delete that week's schedule
                # But we don't have the target list here easily unless we store it.
                # Simpler: Delete range from min to max.
                
                session.query(Schedule).filter(Schedule.date >= min_date, Schedule.date <= max_date).delete()
            
            # Add all from result
            db_schedules = []
            for s in new_schedules:
                new_s = Schedule(date=s.date, user_id=s.user.id, is_locked=s.is_locked)
                db_schedules.append(new_s)
            
            session.add_all(db_schedules)
            session.commit()
            session.close()
            
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
        default_filename = f"{year}年{month}月排班表.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出Excel", 
            default_filename,  # Set default filename
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Need to filter schedules for this month/view?
                # For now, export ALL schedules or visible ones?
                # Let's export visible ones (current month)
                # But wait, our 'schedules' list contains ALL.
                # Let's filter by current view month.
                
                # Logic: Filter schedules that fall in current month (or extended view)
                # Simple: Filter by year and month of current view
                
                target_schedules = [
                    s for s in self.schedules 
                    if s.date.year == year and s.date.month == month
                ]
                
                # If target_schedules is empty, maybe export everything or warn?
                # User might want to export what they see.
                # If they see adjacent months, they might want those too.
                # But typically "Export" means the current month's report.
                
                # Fallback: if empty, export all? No, that's confusing.
                # Let's stick to current month filter.
                
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
            session = self.db_manager.get_session()
            
            # 1. Handle Move (if source_date is provided)
            if source_date:
                # Remove from source date
                old_sch = session.query(Schedule).filter_by(date=source_date, user_id=user_id).first()
                if old_sch:
                    session.delete(old_sch)
            
            # 2. Check existence in target date
            existing = session.query(Schedule).filter_by(date=date, user_id=user_id).first()
            if existing:
                # Already there
                session.commit() # Commit deletion if any
                session.close()
                self.reload_data() # Refresh to reflect move if happened
                return

            # 3. Add to target date
            new_sch = Schedule(date=date, user_id=user_id, is_locked=True) # Manual drop = Locked?
            session.add(new_sch)
            session.commit()
            session.close()
            
            self.reload_data()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新排班失败: {str(e)}")

    def handle_user_removed(self, date, user_id):
        try:
            session = self.db_manager.get_session()
            sch = session.query(Schedule).filter_by(date=date, user_id=user_id).first()
            if sch:
                session.delete(sch)
                session.commit()
            session.close()
            self.reload_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除人员失败: {str(e)}")

    def handle_day_cleared(self, date):
        try:
            session = self.db_manager.get_session()
            session.query(Schedule).filter_by(date=date).delete()
            session.commit()
            session.close()
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
