import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import Qt
import datetime

from src.statistics_manager import StatisticsManager

class StatsView(QWidget):
    def __init__(self, users, schedules):
        super().__init__()
        self.users = users
        self.schedules = schedules
        self.stats_manager = StatisticsManager(self.schedules, self.users)
        
        self.layout = QVBoxLayout(self)
        
        # 控制栏
        self._init_controls()
        
        # 图表区域
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        
        # 初始绘制
        self.refresh_charts()

    def _init_controls(self):
        controls_layout = QHBoxLayout()
        
        # 1. 图表类型
        controls_layout.addWidget(QLabel("图表类型:"))
        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems(["班次统计", "长期趋势"])
        self.combo_chart_type.currentIndexChanged.connect(self.on_chart_type_changed)
        controls_layout.addWidget(self.combo_chart_type)
        
        # 2. 统计周期 (仅针对班次统计)
        self.lbl_cycle = QLabel("统计周期:")
        controls_layout.addWidget(self.lbl_cycle)
        
        self.combo_cycle = QComboBox()
        self.combo_cycle.addItems(["按月统计", "按年统计"])
        self.combo_cycle.currentIndexChanged.connect(self.on_cycle_changed)
        controls_layout.addWidget(self.combo_cycle)
        
        # 3. 年份选择
        self.lbl_year = QLabel("年份:")
        controls_layout.addWidget(self.lbl_year)
        
        self.combo_year = QComboBox()
        current_year = datetime.date.today().year
        # 提供前后几年的选项
        years = [str(y) for y in range(current_year - 2, current_year + 4)]
        self.combo_year.addItems(years)
        self.combo_year.setCurrentText(str(current_year))
        self.combo_year.currentIndexChanged.connect(self.refresh_charts)
        controls_layout.addWidget(self.combo_year)
        
        # 4. 月份选择
        self.lbl_month = QLabel("月份:")
        controls_layout.addWidget(self.lbl_month)
        
        self.combo_month = QComboBox()
        self.combo_month.addItems([str(i) for i in range(1, 13)])
        self.combo_month.setCurrentText(str(datetime.date.today().month))
        self.combo_month.currentIndexChanged.connect(self.refresh_charts)
        controls_layout.addWidget(self.combo_month)
        
        controls_layout.addStretch()
        self.layout.addLayout(controls_layout)

    def on_chart_type_changed(self):
        ctype = self.combo_chart_type.currentText()
        is_stats = (ctype == "班次统计")
        
        self.lbl_cycle.setVisible(is_stats)
        self.combo_cycle.setVisible(is_stats)
        
        # Trigger cycle change to update year/month visibility
        if is_stats:
            self.on_cycle_changed()
        else:
            # If trend, maybe hide cycle/year/month or keep year/month as range end?
            # For simplicity, let's keep Year/Month visible as "End Date" for trend?
            # Or just hide cycle and keep Year/Month as reference?
            # Original code used "today" for trend end date.
            # Let's hide cycle but keep Year/Month to define the "view point".
            self.lbl_year.setVisible(True)
            self.combo_year.setVisible(True)
            self.lbl_month.setVisible(True)
            self.combo_month.setVisible(True)
            
        self.refresh_charts()

    def on_cycle_changed(self):
        cycle = self.combo_cycle.currentText()
        is_monthly = (cycle == "按月统计")
        
        self.lbl_month.setVisible(is_monthly)
        self.combo_month.setVisible(is_monthly)
        
        self.refresh_charts()

    def update_data(self, schedules, users=None):
        self.schedules = schedules
        if users is not None:
            self.users = users
        self.stats_manager = StatisticsManager(self.schedules, self.users)
        self.refresh_charts()

    def refresh_charts(self):
        self.figure.clear()
        chart_type = self.combo_chart_type.currentText()
        
        year = int(self.combo_year.currentText())
        month = int(self.combo_month.currentText())
        
        if chart_type == "班次统计":
            cycle = self.combo_cycle.currentText()
            if cycle == "按月统计":
                self._draw_bar_chart(year, month, is_annual=False)
            else:
                self._draw_bar_chart(year, month, is_annual=True)
        elif chart_type == "长期趋势":
            self._draw_trend_line_chart(year, month)
            
        self.canvas.draw()

    def _draw_bar_chart(self, year, month, is_annual):
        ax = self.figure.add_subplot(111)
        
        if is_annual:
            stats = self.stats_manager.get_annual_stats(year)
            title = f"{year}年 年度班次统计"
        else:
            stats = self.stats_manager.get_monthly_stats(year, month)
            title = f"{year}年{month}月 班次统计"
        
        # Map codes to names
        user_map = {u.code: (u.name if u.name else u.code) for u in self.users}
        
        # Sort by count desc? or by name? Or default order?
        # Usually consistent order is better. Let's sort by count desc.
        # But maybe user order is better for finding people.
        # Let's use the order of self.users to keep X-axis consistent
        
        names = []
        counts = []
        
        for user in self.users:
            display_name = user.name if user.name else user.code
            names.append(display_name)
            counts.append(stats.get(user.code, 0))
        
        # 绘制柱状图
        bars = ax.bar(names, counts, color='#007AFF', alpha=0.7)
        
        ax.set_title(title)
        ax.set_ylabel("班次数量")
        
        # Dynamic Y-limit
        if counts:
            ax.set_ylim(0, max(counts) * 1.2 if max(counts) > 0 else 5)
        else:
            ax.set_ylim(0, 5)
        
        # X-axis labels rotation if many users
        if len(names) > 10:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')

    def _draw_trend_line_chart(self, year, month):
        ax = self.figure.add_subplot(111)
        
        # Define range based on selection
        # End date = selected year/month's last day
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime.date(year, month, last_day)
        
        # Start date = 30 days before? or 1st of month?
        # "长期趋势" usually implies a window. 
        # Let's show: Start of Year to Selected Month End? Or just surrounding?
        # Existing logic was "Next 30 days" or "Current Month".
        # Let's show "Year to Date" trend if it's long term?
        # Or just +/- 15 days around selection?
        # Let's stick to "Current Month Trend" for now, or "Last 30 days ending on selection".
        # Let's do: First day of selected month -> Last day of selected month.
        start_date = datetime.date(year, month, 1)
        
        trend_data, date_range = self.stats_manager.get_long_term_trend(start_date, end_date)
        
        # x轴格式化
        x_dates = [d.strftime("%d") for d in date_range]
        
        user_map = {u.code: (u.name if u.name else u.code) for u in self.users}

        for user_code, counts in trend_data.items():
            name = user_map.get(user_code, user_code)
            ax.plot(x_dates, counts, label=name, marker='o', markersize=3)
            
        ax.set_title(f"{year}年{month}月 累计班次趋势")
        ax.set_xlabel("日期")
        ax.set_ylabel("累计班次")
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        self.figure.tight_layout()
