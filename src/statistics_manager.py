from collections import defaultdict
import datetime
from typing import List, Dict
from src.models import Schedule, User

class StatisticsManager:
    def __init__(self, schedules: List[Schedule], users: List[User]):
        self.schedules = schedules
        self.users = users

    def get_monthly_stats(self, year: int, month: int) -> Dict[str, int]:
        """
        计算指定月份每人的排班天数
        :return: {user_code: count}
        """
        stats = defaultdict(int)
        # 初始化所有用户为0，确保都在结果中
        for user in self.users:
            stats[user.code] = 0
            
        for sch in self.schedules:
            if sch.date.year == year and sch.date.month == month:
                # Ensure we handle cases where user might have been deleted but schedule remains (though logic usually prevents this)
                if hasattr(sch.user, 'code'):
                     stats[sch.user.code] += 1
                
        return dict(stats)

    def get_annual_stats(self, year: int) -> Dict[str, int]:
        """
        计算指定年份每人的排班天数
        :return: {user_code: count}
        """
        stats = defaultdict(int)
        for user in self.users:
            stats[user.code] = 0
            
        for sch in self.schedules:
            if sch.date.year == year:
                if hasattr(sch.user, 'code'):
                    stats[sch.user.code] += 1
                
        return dict(stats)

    def get_weekend_stats(self, year: int, month: int = None) -> Dict[str, int]:
        """
        计算指定年份(或月份)每人的周末值班天数
        :return: {user_code: count}
        """
        stats = defaultdict(int)
        for user in self.users:
            stats[user.code] = 0
            
        for sch in self.schedules:
            if sch.date.year == year:
                if month is not None and sch.date.month != month:
                    continue
                    
                # 5=Saturday, 6=Sunday
                if sch.date.weekday() >= 5:
                    if hasattr(sch.user, 'code'):
                        stats[sch.user.code] += 1
                
        return dict(stats)

    def get_monthly_variance(self, year: int, month: int) -> float:
        """
        计算月度班次差异 (最大班次数 - 最小班次数)
        """
        stats = self.get_monthly_stats(year, month)
        counts = list(stats.values())
        if not counts:
            return 0
        return max(counts) - min(counts)

    def get_long_term_trend(self, start_date: datetime.date, end_date: datetime.date) -> Dict[str, List[int]]:
        """
        获取一段时间内每人的累计排班趋势
        :return: {user_code: [cumulative_count_day1, cumulative_count_day2, ...]}
        """
        # 生成日期序列
        delta = (end_date - start_date).days + 1
        date_range = [start_date + datetime.timedelta(days=i) for i in range(delta)]
        
        trend_data = {user.code: [0] * delta for user in self.users}
        
        # 预处理排班数据，加速查询
        sch_map = defaultdict(list)
        for sch in self.schedules:
            sch_map[sch.date].append(sch.user.code)
            
        # 计算每日累计
        current_counts = defaultdict(int)
        
        for i, date in enumerate(date_range):
            # 更新当日排班
            if date in sch_map:
                for code in sch_map[date]:
                    current_counts[code] += 1
            
            # 记录当日累计值
            for user in self.users:
                trend_data[user.code][i] = current_counts[user.code]
                
        return trend_data, date_range
