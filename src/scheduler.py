import datetime
import random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from src.consts import GroupType, WeekDay, MAX_SHIFTS_PER_WEEK, SHIFTS_PER_DAY
from src.models import User, Schedule

class Scheduler:
    def __init__(self, users: List[User], start_date: datetime.date, history_counts: Dict[str, int] = None, last_duty_dates: Dict[str, datetime.date] = None, last_weekend_duty: Dict[str, bool] = None, weekend_history_counts: Dict[str, int] = None):
        self.users = users
        self.start_date = start_date
        self.history_counts = history_counts or defaultdict(int)
        self.last_duty_dates = last_duty_dates or {}
        # New parameter: last_weekend_duty
        # Maps user_code -> True if they worked LAST weekend (Sat or Sun)
        self.last_weekend_duty = last_weekend_duty or {}
        self.weekend_history_counts = weekend_history_counts or defaultdict(int)
        self.rotation_exclusions: Dict[datetime.date, set] = defaultdict(set)
        
        # 确保 start_date 是周一
        if self.start_date.weekday() != 0:
            raise ValueError("Start date must be a Monday")
        
        self.schedule_result: Dict[datetime.date, List[User]] = defaultdict(list)
        self.user_week_counts: Dict[str, int] = defaultdict(int)
        
        # 安全性控制
        self.max_steps = 50000 
        self.steps = 0
        self.last_error = None # Store error reason if scheduling fails
        
        # 初始化用户计数
        for user in self.users:
            self.user_week_counts[user.code] = 0

    def _get_holiday_name(self, date: datetime.date) -> Optional[str]:
        """获取日期的节假日名称 (简单硬编码 2025 年示例)"""
        # In a real app, this should be a config or external API
        year = date.year
        md = (date.month, date.day)
        
        # 简单支持跨年 (假设只处理 2024-2026)
        # 这里仅作演示，实际应引入该国节假日库
        if md == (1, 1): return "元旦"
        if md in [(5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]: return "劳动节"
        if md in [(10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)]: return "国庆节"
        
        # 2025 Specific (Approximate Lunar)
        if year == 2025:
            if md in [(1, 28), (1, 29), (1, 30), (1, 31), (2, 1), (2, 2), (2, 3), (2, 4)]: return "春节"
            if md in [(4, 4), (4, 5), (4, 6)]: return "清明节"
            if md in [(5, 31), (6, 1), (6, 2)]: return "端午节"
            if md in [(10, 6), (10, 7)]: return "中秋节" # 2025 Mid-Autumn is Oct 6
            
        return None

    def is_available(self, user: User, date: datetime.date) -> bool:
        """检查用户在特定日期是否可用（基于偏好和分组规则）"""
        
        # 1. 检查黑名单 (Preferences)
        if user.preferences and isinstance(user.preferences, dict):
            blackout_dates = user.preferences.get("blackout_dates", [])
            date_str = date.strftime("%Y-%m-%d")
            if date_str in blackout_dates:
                return False
                
            # Check unavailable weekdays
            unavailable_weekdays = user.preferences.get("unavailable_weekdays", [])
            if date.weekday() in unavailable_weekdays:
                return False
                
        weekday = date.weekday()  # 0=Mon, 6=Sun
        
        # 2. 检查 Legacy GroupType (仅当未设置偏好时回退，或者保留作为基础规则)
        # 为保持灵活性，如果 GroupType 是 UNLIMITED，则完全由 preferences 决定
        if user.group_type == GroupType.UNLIMITED:
            return True
        
        if user.group_type == GroupType.RESTRICTED_FG:
            # 仅可排周一(0)/三(2)/五(4)
            return weekday in [0, 2, 4]
            
        if user.group_type == GroupType.SINGLE_H:
            # 仅可排周二(1)/三(2)/四(3)
            return weekday in [1, 2, 3]
            
        return False

    def get_user_priority(self, user: User) -> int:
        """
        获取用户优先级数值 (1=最高, 3=最低)
        默认为 3 (最低)
        """
        if user.preferences and isinstance(user.preferences, dict):
            p_str = self._get_employee_type(user.preferences)
            if p_str == "一级": return 1
            if p_str == "二级": return 2
            if p_str == "三级": return 3
        return 3 # Default to Level 3

    def _get_preferred_weekdays(self, prefs: dict) -> List[int]:
        preferred = prefs.get("preferred_weekdays", None)
        if preferred is None:
            preferred = prefs.get("preferred_days", [])
        if not preferred:
            return []
        normalized: List[int] = []
        for v in preferred:
            try:
                normalized.append(int(v))
            except (ValueError, TypeError):
                continue
        return normalized

    def _get_employee_type(self, prefs: dict) -> str:
        raw = prefs.get("employee_type", None)
        mapping = {"一类": "一级", "二类": "二级", "三类": "三级"}
        if raw in mapping:
            return mapping[raw]
        if raw in ("一级", "二级", "三级"):
            return raw
        preferred = set(self._get_preferred_weekdays(prefs))
        unavailable_weekdays = prefs.get("unavailable_weekdays", [])
        unavailable = set()
        for v in unavailable_weekdays:
            try:
                unavailable.add(int(v))
            except (ValueError, TypeError):
                continue
        if preferred:
            available = set(range(7)) - unavailable
            if available == preferred:
                return "一级"
        return "三级"

    def check_constraints(self, user: User, date: datetime.date, strict: bool = True) -> bool:
        """
        检查用户是否能被安排在指定日期
        规则：
        1. 每周值班不超过3次 (Rule 1)
        2. 员工等级限制 (Rule 2 & 3)
           - 一级员工偏好必须满足
           - 三级员工只能在偏好日轮班 (Rule 3 in _apply_rotation_rules, but generalized?)
        3. 不可值班日期
        4. 周末连班检查 (Rule 1 part 2: 如果安排周六，必须能安排周日)
        """
        prefs = user.preferences or {}
        
        # 0. 基础硬性限制：不可值班日期
        unavailable = prefs.get("unavailable_dates", [])
        blackouts = prefs.get("blackout_dates", [])
        date_str = date.strftime("%Y-%m-%d")
        if date_str in unavailable or date_str in blackouts:
            return False
        unavailable_weekdays = prefs.get("unavailable_weekdays", [])
        if date.weekday() in unavailable_weekdays:
            return False

        # 0.5 检查当天是否已经排了该用户 (Move up for early exit)
        if user in self.schedule_result[date]:
            return False
        if user.code in self.rotation_exclusions.get(date, set()):
            return False

        # --- 一级人员特殊处理：绝对优先 (Level 1 Override) ---
        emp_type = self._get_employee_type(prefs)
        if emp_type == "一级":
            preferred_days = self._get_preferred_weekdays(prefs)
            # 规则：一级人员必须只在期望日值班
            if preferred_days and date.weekday() not in preferred_days:
                return False
            
            # 规则：节假日回避
            avoid_hols = prefs.get("avoid_holidays", [])
            if avoid_hols:
                hol_name = self._get_holiday_name(date)
                if hol_name and hol_name in avoid_hols:
                    return False
            
            # 满足上述硬性条件后，一级人员直接通过（忽略排班数量、周末连班等限制）
            return True
        # ----------------------------------------------------

        # 1. 数量限制
        # 注意：如果是周六，我们需要预判周日也排班，所以如果是周六，当前必须 <= MAX-2 (因为 Sat+Sun=2)
        # 如果是周日，理论上必须是周六已排的人，这里只需检查 <= MAX
        current_shifts = self.user_week_counts[user.code]
        if prefs.get("preferred_cycle") == "每两周 (隔周)":
            last_duty = self.last_duty_dates.get(user.code)
            if last_duty and (date - last_duty).days < 14:
                return False
        if date.weekday() == 5: # Saturday
            if current_shifts + 2 > MAX_SHIFTS_PER_WEEK:
                return False
            
            sunday_date = date + datetime.timedelta(days=1)
            sunday_str = sunday_date.strftime("%Y-%m-%d")
            if sunday_str in unavailable:
                return False
            
            emp_type = self._get_employee_type(prefs)
            if emp_type == "一级":
                preferred_days = self._get_preferred_weekdays(prefs)
                if preferred_days and 6 not in preferred_days:
                    return False
        elif date.weekday() == 6: # Sunday
            if current_shifts >= MAX_SHIFTS_PER_WEEK:
                return False
        else:
            if current_shifts >= MAX_SHIFTS_PER_WEEK:
                return False

        # 2. 检查当天是否已经排了该用户 (Removed - Moved to top)
        # (Logic moved to step 0.5)

        # 3. 员工等级与偏好 (Rule 2)
        # emp_type check moved to top for Level 1 bypass
        
        # 3.5 Level 2/3 Preference Check
        preferred_days = self._get_preferred_weekdays(prefs)
        
        # 4. 节假日回避 (Legacy/Optional)

        avoid_hols = prefs.get("avoid_holidays", [])
        if avoid_hols:
            hol_name = self._get_holiday_name(date)
            if hol_name and hol_name in avoid_hols:
                if emp_type == "一级":
                    return False

        # 5. 周末冷却 (Hard Constraint in Strict Mode) - Rule 4
        # "Do not appear" -> Strict prohibition if strict=True
        if strict and date.weekday() >= 5:
            if self.last_weekend_duty.get(user.code, False):
                return False

        return True

    def generate_schedule(self, existing_schedules: List[Schedule] = None, mode: str = "all") -> List[Schedule]:
        """
        使用回溯法生成排班表
        :param existing_schedules: 已有的排班记录（如锁定的排班），算法将在此基础上补充
        :param mode: "all" (Default), "level1_only", "fill_rest"
        """
        # 备份初始状态，以便重试
        initial_schedule_result = defaultdict(list)
        initial_user_week_counts = self.user_week_counts.copy()
        
        # 预处理现有排班
        if existing_schedules:
            for sch in existing_schedules:
                # 只处理本周内的
                if self.start_date <= sch.date < self.start_date + datetime.timedelta(days=7):
                    # 防止重复添加
                    if sch.user not in initial_schedule_result[sch.date]:
                        initial_schedule_result[sch.date].append(sch.user)
                        initial_user_week_counts[sch.user.code] += 1
                        
        dates = [self.start_date + datetime.timedelta(days=i) for i in range(7)]

        # 尝试策略 1: 严格模式 (Strict = True)
        self.schedule_result = defaultdict(list)
        for k, v in initial_schedule_result.items():
            self.schedule_result[k] = list(v)
            
        self.user_week_counts = initial_user_week_counts.copy()
        
        # Determine Mode: "Level1 Only" vs "Standard"
        # If fill_rest, we assume Level 1 is already handled or we just skip fixed assignment step if needed?
        # Actually, _apply_level1 checks "if user in self.schedule_result ... continue".
        # So it's safe to run it again.
        
        self._apply_level1_fixed_assignments()
        self._apply_rotation_rules()
        self._apply_fg_rules()
        self._apply_h_rules()
        
        if mode == "level1_only":
            # Just return what we have from fixed assignments
            return self.get_result_list()
            
        self.steps = 0
        
        # If strict=True passed to generate_schedule? (Not currently supported)
        # Let's assume we want to support a mode where we stop here if requested.
        # But for now, let's keep the existing flow.
        
        if self._backtrack(dates, 0, 0, strict=True):
            return self.get_result_list()
        
        # 如果严格模式失败，先生成分析报告
        strict_failure_analysis = self.analyze_failure(dates)
        
        # 尝试策略 2: 宽松模式 (Strict = False)
        # Reset state
        self.schedule_result = defaultdict(list)
        for k, v in initial_schedule_result.items():
            self.schedule_result[k] = list(v)
        self.user_week_counts = initial_user_week_counts.copy()
        
        self._apply_level1_fixed_assignments()
        self._apply_rotation_rules()
        self._apply_fg_rules()
        self._apply_h_rules()
        self.steps = 0
        
        if self._backtrack(dates, 0, 0, strict=False):
            # 宽松模式成功，说明是一级人员偏好以外的软约束（如周末冷却）导致严格模式失败
            # 这种情况下，不应该报错说"一级人员偏好无法满足"，而是提示放宽了规则
            self.last_error = "警告：由于严格约束下无解，系统已自动放宽周末冷却规则以完成排班。"
            return self.get_result_list()
            
        # 宽松模式也失败，说明存在硬性冲突（主要是一级人员偏好或人手不足）
        # 使用之前的分析报告
        self.last_error = strict_failure_analysis
        return []

    def _apply_level1_fixed_assignments(self):
        """
        固定安排一级人员在其期望值班日
        策略：
        1. 激进策略：完全按照一级人员的"期望值班日"进行排班，不考虑轮班互斥。
        2. 后续清理：由 _apply_rotation_rules 负责检测冲突并移除不该值班的搭档。
        """
        for user in self.users:
            prefs = user.preferences or {}
            if self._get_employee_type(prefs) != "一级":
                continue
            preferred_days = self._get_preferred_weekdays(prefs)
            if not preferred_days:
                # 若未设置期望日，则不进行固定安排
                continue
            for day_idx in preferred_days:
                target_date = self.start_date + datetime.timedelta(days=day_idx)
                
                # [Change] 不再在此处检查轮班逻辑，全部先排上
                
                # 已排满或已包含该用户跳过
                if len(self.schedule_result[target_date]) >= SHIFTS_PER_DAY:
                    continue
                if user in self.schedule_result[target_date]:
                    continue
                
                # 即使是严格模式，对于一级人员，只要没有硬性黑名单冲突，check_constraints 都会通过
                if self.check_constraints(user, target_date, strict=True):
                    self.schedule_result[target_date].append(user)
                    self.user_week_counts[user.code] += 1

    def _apply_h_rules(self):
        """
        应用 H 的特殊排班规则：
        1. 固定周二
        2. 固定周四
        """
        user_h = next((u for u in self.users if u.code == 'H' and u.group_type == GroupType.SINGLE_H), None)
        if not user_h:
            return

        # 周二 (Index 1)
        tue_date = self.start_date + datetime.timedelta(days=1)
        if self.check_constraints(user_h, tue_date):
            self.schedule_result[tue_date].append(user_h)
            self.user_week_counts[user_h.code] += 1

        # 周四 (Index 3)
        thu_date = self.start_date + datetime.timedelta(days=3)
        if self.check_constraints(user_h, thu_date):
            self.schedule_result[thu_date].append(user_h)
            self.user_week_counts[user_h.code] += 1

    def _apply_fg_rules(self):
        """
        应用 F/G 的特殊排班规则：
        1. 周一固定 F
        2. 周三固定 G
        3. 周五 F/G 轮替 (基于周数奇偶性)
        """
        user_f = next((u for u in self.users if u.code == 'F' and u.group_type == GroupType.RESTRICTED_FG), None)
        user_g = next((u for u in self.users if u.code == 'G' and u.group_type == GroupType.RESTRICTED_FG), None)
        
        if not user_f or not user_g:
            return

        # 周一 (Index 0)
        mon_date = self.start_date
        if self.check_constraints(user_f, mon_date):
            self.schedule_result[mon_date].append(user_f)
            self.user_week_counts[user_f.code] += 1

        # 周三 (Index 2)
        wed_date = self.start_date + datetime.timedelta(days=2)
        if self.check_constraints(user_g, wed_date):
            self.schedule_result[wed_date].append(user_g)
            self.user_week_counts[user_g.code] += 1

        # 周五 (Index 4)
        fri_date = self.start_date + datetime.timedelta(days=4)
        # 获取 ISO 周号
        week_num = fri_date.isocalendar()[1]
        
        target_user = user_f if week_num % 2 == 1 else user_g # 奇数周 F，偶数周 G
        
        if self.check_constraints(target_user, fri_date):
            self.schedule_result[fri_date].append(target_user)
            self.user_week_counts[target_user.code] += 1

    def _apply_rotation_rules(self):
        processed = set()
        
        for user in self.users:
            prefs = user.preferences or {}
            rot_pref = prefs.get("periodic_rotation")
            if not rot_pref:
                continue
            partner_code = rot_pref.get("partner")
            day_idx = rot_pref.get("day_idx")
            # Robust Type Cast
            try:
                day_idx = int(day_idx) if day_idx is not None else None
            except (ValueError, TypeError):
                continue
                
            parity = rot_pref.get("parity", "odd")
            if not partner_code or day_idx is None:
                continue
            target_date = self.start_date + datetime.timedelta(days=day_idx)
            pair_key = (target_date, tuple(sorted([user.code, partner_code])))
            if pair_key in processed:
                continue
            processed.add(pair_key)
            partner = next((u for u in self.users if u.code == partner_code), None)
            if not partner:
                continue
            week_num = target_date.isocalendar()[1]
            is_odd_week = (week_num % 2 != 0)
            # Determine who is on duty
            if (parity == "odd" and is_odd_week) or (parity == "even" and not is_odd_week):
                selected_user = user
                other_user = partner
            else:
                selected_user = partner
                other_user = user
            
            # 1. 无论 selected_user 是否已安排，other_user 都必须被排除
            self.rotation_exclusions[target_date].add(other_user.code)
            
            # Safety Net: 如果 other_user 在之前的步骤（如一级固定）中被错误安排了，立即移除
            if other_user in self.schedule_result[target_date]:
                self.schedule_result[target_date].remove(other_user)
                self.user_week_counts[other_user.code] -= 1
            
            sel_prefs = selected_user.preferences or {}
            emp_type_sel = self._get_employee_type(sel_prefs)
            preferred_days_sel = self._get_preferred_weekdays(sel_prefs)
            if emp_type_sel == "一级" and preferred_days_sel and day_idx not in preferred_days_sel:
                continue

            # 2. 尝试安排 selected_user (如果尚未安排)
            if selected_user in self.schedule_result[target_date]:
                continue

            if self.check_constraints(selected_user, target_date, strict=True):
                if len(self.schedule_result[target_date]) < SHIFTS_PER_DAY:
                    self.schedule_result[target_date].append(selected_user)
                    self.user_week_counts[selected_user.code] += 1

    def _backtrack(self, dates: List[datetime.date], day_idx: int, slot_idx: int, strict: bool) -> bool:
        """
        递归回溯填充
        :param dates: 本周日期列表
        :param day_idx: 当前处理的日期索引 (0-6)
        :param slot_idx: 当前处理的班次索引 (0-1, 每天2班)
        """
        self.steps += 1
        if self.steps > self.max_steps:
            # 超过最大尝试次数，停止搜索
            return False

        # 如果所有日期都处理完了，成功
        if day_idx >= 7:
            return True
        
        current_date = dates[day_idx]
        
        # 计算下一个状态的索引
        next_slot = slot_idx + 1
        next_day = day_idx
        if next_slot >= SHIFTS_PER_DAY:
            next_slot = 0
            next_day = day_idx + 1
            
        # 检查当前位置是否已经被预占 (Locked/Existing)
        if len(self.schedule_result[current_date]) > slot_idx:
            # 当前位置已有安排，直接跳过，处理下一个
            return self._backtrack(dates, next_day, next_slot, strict)

        # 获取候选人列表
        # 优化策略：优先选择当前排班数较少的人，增加随机性以避免每次结果一样
        # 特殊规则：周末同人 (Saturday Sunday fixed same 2 people)
        # 如果是周日 (6)，候选人只能是周六 (5) 已排的人
        if current_date.weekday() == 6:
            saturday_date = current_date - datetime.timedelta(days=1)
            saturday_users = self.schedule_result[saturday_date]
            
            # FIX: Ensure strict order matching with Saturday (Top->Top, Bottom->Bottom)
            if slot_idx < len(saturday_users):
                candidates = [saturday_users[slot_idx]]
            else:
                candidates = list(saturday_users)
            
            # 如果周六没人（异常情况），说明状态不对，回溯
            if not candidates:
                return False
        else:
            candidates = list(self.users)
        
            # 简单启发式：
            # 1. 优先选择期望在今天值班的人 (Priority Boost)
            #    - 如果用户偏好包含今天 (preferred_weekdays)，给予最高优先级
            # 2. 优先级排序：一级 > 二级 > 三级
            # 3. 优先当前排班数少的 (硬约束)
            # 4. 其次历史排班总数少的 (软均衡)
            # 5. 随机打乱 (避免死板)
            random.shuffle(candidates) 
        
        def calculate_score(user):
            """
            计算候选人得分，分数越低越优先
            考虑因素：
            1. 总排班数均衡 (History + Current) (Rule 5)
            2. 员工等级 (二级 > 三级) (Rule 2)
            3. 偏好匹配 (Bonus)
            4. 周末避免连排 (Penalty) (Rule 4)
            """
            score = 0.0
            code = user.code
            prefs = user.preferences or {}
            emp_type = self._get_employee_type(prefs)
            
            # 1. 均衡性 (Balance)
            if emp_type != "一级":
                group_users = [u for u in self.users if self._get_employee_type(u.preferences or {}) == emp_type]
                group_totals = [self.history_counts.get(u.code, 0) + self.user_week_counts[u.code] for u in group_users]
                group_avg = (sum(group_totals) / len(group_totals)) if group_totals else 0
                candidate_total = self.history_counts.get(code, 0) + self.user_week_counts[code]
                score += (candidate_total - group_avg) * 1000 

            # New: Weekend Balance
            # 如果是周末，优先选择周末值班总数较少的人
            if current_date.weekday() >= 5:
                weekend_total = self.weekend_history_counts.get(code, 0)
                # 加上本周已排的周末班次（例如正在排周日，需考虑周六）
                for d, scheduled_users in self.schedule_result.items():
                    if d.weekday() >= 5 and user in scheduled_users:
                        weekend_total += 1
                
                score += weekend_total * 5000 # 给予更高的权重以平衡周末
            
            # 2. 员工等级优先度 (Priority) - STRICT TIERING
            # 必须保证 一级 > 二级 > 三级
            # 权重必须远大于均衡分 (1000/shift)，确保跨等级不通过均衡来竞争
            if emp_type == "一级":
                score -= 10000000 # Absolute Priority
            elif emp_type == "二级":
                score -= 5000000  # High Priority
            elif emp_type == "三级":
                score += 0        # Base Priority

                
            # 3. 偏好匹配 (Preference Bonus)
            # 对于二级/三级员工，尽量满足偏好
            preferred_days = self._get_preferred_weekdays(prefs)
            if preferred_days and current_date.weekday() in preferred_days:
                score -= 500 # 给予很大优惠，使其优先于无偏好的人

            # 3.5. 期望排班搭档 (Level 1 Preferred Partners)
            # 检查当天已排的一级人员是否期望当前候选人
            for scheduled_user in self.schedule_result[current_date]:
                s_prefs = scheduled_user.preferences or {}
                if self._get_employee_type(s_prefs) == "一级":
                    partners = s_prefs.get("preferred_partners", [])
                    if code in partners:
                        # Found in preferred list!
                        try:
                            idx = partners.index(code)
                            # Boost logic:
                            # We want preferred partners to be prioritized significantly.
                            # Base Level 2 is -5,000,000. Base Level 3 is 0.
                            # If we want a Preferred Level 3 to beat a Non-Preferred Level 2, we need > 5,000,000 boost.
                            # Let's give 6,000,000 base boost, decreasing by rank.
                            boost = 6000000 - (idx * 10000) 
                            score -= boost
                        except ValueError:
                            pass
                
            # 4. 周末冷却 (Weekend Fairness) - Rule 4
            # "If arranged to weekend... try not to arrange again"
            if current_date.weekday() >= 5:
                # New Logic using last_weekend_duty
                if self.last_weekend_duty.get(code, False):
                     # Massive Penalty to enforce "Try not to" as strongly as possible
                     # Unless they are the ONLY candidates, they should lose to anyone else.
                     # Base balance diff might be ~1000-2000. 
                     # Give 50000 to be safe.
                     score += 50000 
                
                # Also keep the old logic for fallback (if last_weekend_duty not provided or for gap checks)
                last_duty = self.last_duty_dates.get(code)
                if last_duty and isinstance(last_duty, datetime.date):
                    days_diff = (current_date - last_duty).days
                    # If they worked recently (e.g. yesterday or day before), penalty
                    # But if it's the SAME weekend (e.g. Sat -> Sun), we WANT them (for consecutive rule)
                    # Check logic:
                    # If current is Sat(5): Last duty being recent is bad (unless we want consecutive days? No, we want distinct weekends)
                    # If current is Sun(6): Last duty SHOULD be Sat(5) (yesterday).
                    
                    if current_date.weekday() == 6: # Sunday
                         # If last duty was Sat (1 day ago), that is GOOD (Rule 1).
                         # We actually enforce this in candidates list logic.
                         # So here we don't need to penalize Sat->Sun.
                         pass
                    elif current_date.weekday() == 5: # Saturday
                         # If last duty was recent (e.g. Friday), maybe penalty?
                         # User didn't specify.
                         pass

            # 5. 避免连续值班 (Avoid Consecutive Duty)
            # 除了周末 (Sat->Sun) 必须连续外，其余情况尽量避免连续值班
            if current_date.weekday() != 6: # Not Sunday
                yesterday = current_date - datetime.timedelta(days=1)
                worked_yesterday = False
                
                # Case 1: Yesterday was in this scheduling window (e.g. Tue-Sat)
                # self.schedule_result is keyed by date, so we can check directly
                if yesterday in self.schedule_result:
                    if user in self.schedule_result[yesterday]:
                        worked_yesterday = True
                        
                # Case 2: Yesterday was before this window (i.e. Monday checking last Sunday)
                # Check last_duty_dates
                elif current_date.weekday() == 0:
                     last_duty = self.last_duty_dates.get(code)
                     if last_duty and last_duty == yesterday:
                         worked_yesterday = True
                
                if worked_yesterday:
                    # Massive Penalty to avoid consecutive days
                    # Base priority diffs are ~5,000,000.
                    # We want this to be very strong, effectively a soft "hard constraint".
                    score += 20000000

            # 6. 随机扰动 (Random Noise)
            # 为了避免排班过于规律（如总是同样的人凑在一起），引入随机扰动
            # 扰动幅度设定：
            # - 1个班次的均衡分差约为 1000 分
            # - 设定 +/- 2000 分的扰动，意味着允许约 2 个班次的偏差
            # - 这不会打破等级限制 (5,000,000) 或连续值班限制 (20,000,000)
            score += random.uniform(-2000, 2000)
            
            return score

        candidates.sort(key=calculate_score)

        for user in candidates:
            if self.check_constraints(user, current_date, strict):
                # 尝试安排
                self.schedule_result[current_date].append(user)
                self.user_week_counts[user.code] += 1
                
                # 递归下一步
                if self._backtrack(dates, next_day, next_slot, strict):
                    return True
                
                # 回溯：撤销选择
                self.schedule_result[current_date].pop()
                self.user_week_counts[user.code] -= 1
                
        return False

    def analyze_failure(self, dates: List[datetime.date]) -> str:
        """
        Analyze why strict scheduling failed.
        Returns a formatted error string.
        """
        # We simulate a greedy fill to see where it gets stuck
        # Or simpler: Find the first slot where NO candidates are available under strict rules
        
        # We need to reconstruct the state partially? 
        # Actually, since _backtrack modifies state in place and backtracks, the state is clean now.
        # We need to replay to find the failure point.
        
        # Simplified Replay:
        # Just iterate days/slots. The first one we can't fill is the culprit?
        # Not necessarily, because previous choices might be the cause.
        # But for a helpful error message, identifying the first problematic slot is good enough.
        
        report = []
        
        # Re-initialize for analysis
        temp_schedule = defaultdict(list)
        temp_counts = self.user_week_counts.copy() # Use current counts (which should be initial state if backtrack cleaned up)
        
        # Wait, if _backtrack returned False, it should have cleaned up to initial state.
        
        for day_idx, date in enumerate(dates):
            for slot_idx in range(SHIFTS_PER_DAY):
                # Try to find a valid user
                valid_users = []
                for user in self.users:
                    # Check basic hard constraints + Level 1 constraints
                    # We need to manually simulate check_constraints logic here to capture specific reasons
                    
                    reasons = []
                    # 1. Availability
                    if not self.is_available(user, date):
                        reasons.append("不可用(黑名单/分组)")
                    
                    # 2. Max shifts (approximate, since we don't have full history of this replay)
                    # We can't easily check max shifts in this simple scan without tracking state.
                    # Let's just check static constraints for Level 1
                    
                    priority = self.get_user_priority(user)
                    if priority == 1:
                        prefs = user.preferences if user.preferences else {}
                        # Holidays
                        avoid_hols = prefs.get("avoid_holidays", [])
                        if avoid_hols:
                            hol_name = self._get_holiday_name(date)
                            if hol_name and hol_name in avoid_hols:
                                reasons.append("一级人员回避节假日")
                        
                        # Preferred Weekdays
                        preferred_days = prefs.get("preferred_weekdays", [])
                        if preferred_days and date.weekday() not in preferred_days:
                            reasons.append("非一级人员期望工作日")
                            
                    if not reasons:
                        valid_users.append(user)
                
                if not valid_users:
                    # If NO user is valid even without considering dynamic constraints (like max shifts or pairing),
                    # that's a huge problem.
                    # But usually the problem is dynamic.
                    pass

        # Since a full analysis is complex, let's provide a generic but helpful message based on Level 1 users.
        report.append("无法满足所有一级人员的排班偏好。")
        report.append("可能的冲突原因：")
        
        l1_users = [u for u in self.users if self.get_user_priority(u) == 1]
        for user in l1_users:
            prefs = user.preferences or {}
            issues = []
            if prefs.get("preferred_weekdays"):
                days = ",".join([str(d+1) for d in prefs.get("preferred_weekdays")])
                issues.append(f"仅期望周{days}")
            if prefs.get("avoid_holidays"):
                issues.append("回避节假日")
            if issues:
                report.append(f"- {user.name}: {'; '.join(issues)}")
                
        if not l1_users:
             report.append("- 未找到一级人员，可能是其他硬性约束导致失败。")
             
        return "\n".join(report)

    def get_result_list(self) -> List[Schedule]:
        """将结果转换为 Schedule 对象列表"""
        result = []
        for date, users in self.schedule_result.items():
            for user in users:
                result.append(Schedule(date=date, user_id=user.id, user=user))
        return result
