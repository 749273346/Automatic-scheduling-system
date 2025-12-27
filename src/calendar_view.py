import datetime
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QVBoxLayout, 
                             QFrame, QPushButton, QHBoxLayout, QMessageBox, QDialog, QDialogButtonBox, QMenu, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QColor, QDrag, QPixmap

from src.consts import WeekDay, GroupType

class ScheduleItemLabel(QLabel):
    """
    可拖拽、支持右键菜单的排班人员标签
    """
    remove_requested = pyqtSignal(str) # user_id

    def __init__(self, user_id, user_code, date, color="#007AFF", parent=None):
        super().__init__(user_code, parent)
        self.user_id = user_id
        self.user_code = user_code
        self.date = date
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border-radius: 4px;
            padding: 4px 0px;
            font-size: 12px;
            font-weight: 600;
        """)
        
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            # Format: user_id,user_code,source_date_str
            date_str = self.date.strftime("%Y-%m-%d")
            mime.setText(f"{self.user_id},{self.user_code},{date_str}")
            drag.setMimeData(mime)
            
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setHotSpot(e.pos())
            
            drag.exec_(Qt.MoveAction)
            
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        action_delete = menu.addAction("删除")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == action_delete:
            self.remove_requested.emit(self.user_id)

class MonthPickerDialog(QDialog):
    def __init__(self, current_date, parent=None):
        super().__init__(parent)
        self.selected_date = current_date
        self.setWindowTitle("选择月份")
        self.setFixedSize(300, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Year Selector
        h_layout = QHBoxLayout()
        self.btn_prev_year = QPushButton("<<")
        self.btn_prev_year.setFixedSize(30, 30)
        self.btn_prev_year.clicked.connect(self.prev_year)
        
        self.lbl_year = QLabel(str(self.selected_date.year))
        self.lbl_year.setAlignment(Qt.AlignCenter)
        self.lbl_year.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.btn_next_year = QPushButton(">>")
        self.btn_next_year.setFixedSize(30, 30)
        self.btn_next_year.clicked.connect(self.next_year)
        
        h_layout.addWidget(self.btn_prev_year)
        h_layout.addWidget(self.lbl_year)
        h_layout.addWidget(self.btn_next_year)
        layout.addLayout(h_layout)
        
        # Month Grid
        grid = QGridLayout()
        grid.setSpacing(10)
        self.month_buttons = []
        for i in range(12):
            month = i + 1
            btn = QPushButton(f"{month}月")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if month == self.selected_date.month:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #007AFF; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("QPushButton:hover { background-color: #E5E5E5; }")
                
            btn.clicked.connect(lambda checked, m=month: self.on_month_clicked(m))
            grid.addWidget(btn, i // 4, i % 4)
            self.month_buttons.append(btn)
        layout.addLayout(grid)
        
        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def prev_year(self):
        self.selected_date = self.selected_date.replace(year=self.selected_date.year - 1)
        self.lbl_year.setText(str(self.selected_date.year))

    def next_year(self):
        self.selected_date = self.selected_date.replace(year=self.selected_date.year + 1)
        self.lbl_year.setText(str(self.selected_date.year))

    def on_month_clicked(self, month):
        try:
            self.selected_date = self.selected_date.replace(month=month)
            self.accept()
        except ValueError:
            # Handle edge case (e.g. day 31 in a month with 30 days, though we usually set day=1 before passing in)
            pass

class CalendarCell(QFrame):
    # 添加信号，当有数据drop时发射
    # date, user_id, user_code, source_date(optional)
    user_dropped = pyqtSignal(datetime.date, str, str, object) 
    user_removed = pyqtSignal(datetime.date, str) # date, user_id
    day_cleared = pyqtSignal(datetime.date) # date

    def __init__(self, date, parent=None):
        super().__init__(parent)
        self.date = date
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)
        self.setAcceptDrops(True) # 允许拖放
        
        self.default_style = """
            CalendarCell {
                background-color: #FFFFFF;
                border: 1px solid #E5E5EA;
                border-radius: 6px;
            }
            CalendarCell:hover {
                border: 1px solid #007AFF;
                background-color: #F5F9FF;
            }
        """
        self.setStyleSheet(self.default_style)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(2)
        
        # 日期标签
        self.date_label = QLabel(str(date.day))
        self.date_label.setAlignment(Qt.AlignRight)
        self.date_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #1D1D1F; margin-right: 2px;")
        if date.weekday() >= 5: # 周末灰色
            self.date_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #86868B; margin-right: 2px;")
        self.layout.addWidget(self.date_label)
        
        # 排班人员容器
        self.users_layout = QVBoxLayout()
        self.layout.addLayout(self.users_layout)
        self.layout.addStretch()

    def contextMenuEvent(self, event):
        # 只有当该单元格有排班人员时才显示清除菜单
        if self.users_layout.count() > 0:
            menu = QMenu(self)
            action_clear = menu.addAction("清除当日排班")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == action_clear:
                self.day_cleared.emit(self.date)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            # 手动拖拽具有最高优先级，允许放置在任何位置
            # (之前的 strict group constraints 移除，以支持灵活排班)
            event.accept()
            self.setStyleSheet("""
                CalendarCell {
                    background-color: #E3F2FD;
                    border: 2px dashed #007AFF;
                    border-radius: 4px;
                }
            """)
            return
        
        event.ignore()
        
    def dragLeaveEvent(self, event):
        # 恢复默认样式
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event):
        self.setStyleSheet(self.default_style)
        if event.mimeData().hasText():
            data = event.mimeData().text().split(',')
            # format: user_id, user_code, [source_date_str]
            if len(data) >= 2:
                user_id = data[0]
                user_code = data[1]
                
                source_date = None
                if len(data) >= 3 and data[2]:
                    try:
                        source_date = datetime.datetime.strptime(data[2], "%Y-%m-%d").date()
                    except:
                        pass
                
                # 发射信号，由主窗口处理具体的逻辑（如更新数据模型）
                self.user_dropped.emit(self.date, user_id, user_code, source_date)
                
    def _check_group_constraint(self, group_type_str):
        weekday = self.date.weekday()
        if group_type_str == "RESTRICTED_FG":
             # 仅可排周一(0)/三(2)/五(4)
            return weekday in [0, 2, 4]
        if group_type_str == "SINGLE_H":
            # 仅可排周二(1)/三(2)/四(3)
            return weekday in [1, 2, 3]
        return True

    def add_user(self, user_id, user_code, color="#007AFF", tooltip=None):
        lbl = ScheduleItemLabel(user_id, user_code, self.date, color)
        if tooltip:
            lbl.setToolTip(tooltip)
        
        # Connect delete signal
        lbl.remove_requested.connect(lambda uid: self.user_removed.emit(self.date, uid))
        
        self.users_layout.addWidget(lbl)

    def clear_users(self):
        while self.users_layout.count():
            item = self.users_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class CalendarView(QWidget):
    user_dropped = pyqtSignal(datetime.date, str, str, object) # Forward signal
    user_removed = pyqtSignal(datetime.date, str) # date, user_id
    day_cleared = pyqtSignal(datetime.date) # date

    def __init__(self):
        super().__init__()
        self.current_date = datetime.date.today()
        # 调整到当月1号
        self.current_date = self.current_date.replace(day=1)
        
        self.layout = QVBoxLayout(self)
        
        # 顶部控制栏
        self._init_header()
        
        # 日历网格
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        self.layout.addLayout(self.grid_layout)
        
        self.cells = {} # (row, col) -> CalendarCell
        self.schedules_cache = [] # Cache for repainting on month change
        
        self.refresh_calendar()

    @property
    def current_week_start(self):
        """
        返回当前视图（月份）第一天所在周的周一
        """
        # self.current_date 始终是当月1号
        # 计算该日期所在周的周一
        return self.current_date - datetime.timedelta(days=self.current_date.weekday())

    def _init_header(self):
        header = QHBoxLayout()
        header.setContentsMargins(0, 10, 0, 10)
        
        self.btn_prev = QPushButton("  <  ")
        self.btn_prev.setObjectName("CalendarHeaderBtn")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self._prev_month)
        
        self.btn_month = QPushButton()
        self.btn_month.setObjectName("CalendarMonthBtn")
        self.btn_month.setCursor(Qt.PointingHandCursor)
        self.btn_month.setFlat(True)
        self.btn_month.setStyleSheet("""
            QPushButton {
                font-size: 20px; 
                font-weight: bold; 
                color: #333; 
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        self.btn_month.clicked.connect(self._pick_month)
        
        self.btn_next = QPushButton("  >  ")
        self.btn_next.setObjectName("CalendarHeaderBtn")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self._next_month)
        
        header.addWidget(self.btn_prev)
        header.addStretch()
        header.addWidget(self.btn_month)
        header.addStretch()
        header.addWidget(self.btn_next)
        
        self.layout.addLayout(header)
        
        # 星期表头
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        header_grid = QGridLayout()
        header_grid.setContentsMargins(0, 10, 0, 10)
        for i, day in enumerate(days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #86868B; font-weight: 600; font-size: 14px; padding: 5px;")
            header_grid.addWidget(lbl, 0, i)
        self.layout.addLayout(header_grid)

    def refresh_calendar(self):
        # 清除旧格子
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        self.cells.clear()
        
        # 更新标题
        self.btn_month.setText(self.current_date.strftime("%Y年 %m月"))
        
        # 计算日历起始位置
        first_day = self.current_date.replace(day=1)
        start_weekday = first_day.weekday() # 0=Mon
        
        # 填充
        # 这里简化处理，显示 6 周
        current_iter_date = first_day - datetime.timedelta(days=start_weekday)
        
        for row in range(6):
            for col in range(7):
                cell = CalendarCell(current_iter_date)
                
                # 如果不是本月，稍微变灰
                if current_iter_date.month != self.current_date.month:
                    cell.setStyleSheet("CalendarCell { background-color: #FAFAFA; border: 1px solid #EEE; color: #AAA; }")
                
                # 连接信号
                cell.user_dropped.connect(self.user_dropped.emit)
                cell.user_removed.connect(self.user_removed.emit)
                cell.day_cleared.connect(self.day_cleared.emit)

                self.grid_layout.addWidget(cell, row, col)
                self.cells[current_iter_date] = cell
                
                current_iter_date += datetime.timedelta(days=1)

        # Restore schedules from cache
        if self.schedules_cache:
            self.update_schedule(self.schedules_cache)

    def _prev_month(self):
        # 简单处理：减去 20 天再设置为 1 号
        last_month = self.current_date - datetime.timedelta(days=20)
        self.current_date = last_month.replace(day=1)
        self.refresh_calendar()

    def _next_month(self):
        # 简单处理：加上 32 天再设置为 1 号
        next_month = self.current_date + datetime.timedelta(days=32)
        self.current_date = next_month.replace(day=1)
        self.refresh_calendar()

    def _pick_month(self):
        dialog = MonthPickerDialog(self.current_date, self)
        if dialog.exec_() == QDialog.Accepted:
            self.current_date = dialog.selected_date.replace(day=1)
            self.refresh_calendar()
    
    def update_schedule(self, schedules):
        """
        :param schedules: List[Schedule]
        """
        self.schedules_cache = schedules
        
        # 清除所有排班显示
        for cell in self.cells.values():
            cell.clear_users()
            
        for sch in schedules:
            if sch.date in self.cells:
                # Prioritize user's custom color, fallback to default
                color = sch.user.color if sch.user.color else "#007AFF"
                
                # Display name if available, otherwise code
                display_text = sch.user.name if sch.user.name else sch.user.code
                tooltip = f"{sch.user.name} ({sch.user.code})"
                
                # Use str(sch.user.id) to ensure consistency with signal signature
                self.cells[sch.date].add_user(str(sch.user.id), display_text, color, tooltip)
