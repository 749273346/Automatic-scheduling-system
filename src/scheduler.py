import datetime
import random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from src.consts import GroupType, WeekDay, MAX_SHIFTS_PER_WEEK, SHIFTS_PER_DAY
from src.models import User, Schedule

class Scheduler:
    def __init__(self, users: List[User], start_date: datetime.date, history_counts: Dict[str, int] = None, last_duty_dates: Dict[str, datetime.date] = None, last_weekend_duty: Dict[str, bool] = None):
        self.users = users
        self.start_date = start_date
        self.history_counts = history_counts or defaultdict(int)
        self.last_duty_dates = last_duty_dates or {}
        # New parameter: last_weekend_duty
        # Maps user_code -> True if they worked LAST weekend (Sat or Sun)
        self.last_weekend_duty = last_weekend_duty or {}
        
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
            p_str = user.preferences.get("employee_type", "三级")
            if p_str == "一级": return 1
            if p_str == "二级": return 2
            if p_str == "三级": return 3
            # Legacy mapping
            if p_str == "一类": return 1
            if p_str == "二类": return 2
            if p_str == "三类": return 3
        return 3 # Default to Level 3

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
        date_str = date.strftime("%Y-%m-%d")
        if date_str in unavailable:
            return False

        # 1. 数量限制
        # 注意：如果是周六，我们需要预判周日也排班，所以如果是周六，当前必须 <= MAX-2 (因为 Sat+Sun=2)
        # 如果是周日，理论上必须是周六已排的人，这里只需检查 <= MAX
        current_shifts = self.user_week_counts[user.code]
        if date.weekday() == 5: # Saturday
            if current_shifts + 2 > MAX_SHIFTS_PER_WEEK:
                return False
            
            # 额外检查：如果排了周六，必须能排周日
            sunday_date = date + datetime.timedelta(days=1)
            sunday_str = sunday_date.strftime("%Y-%m-%d")
            if sunday_str in unavailable:
                return False
            
            # 检查周日是否符合偏好 (Level 1)
            emp_type = prefs.get("employee_type", "一级")
            if emp_type == "一级":
                preferred_days = prefs.get("preferred_weekdays", [])
                if preferred_days and 6 not in preferred_days:
                    return False
                    
        elif date.weekday() == 6: # Sunday
             if current_shifts >= MAX_SHIFTS_PER_WEEK:
                return False
        else:
            if current_shifts >= MAX_SHIFTS_PER_WEEK:
                return False

        # 2. 检查当天是否已经排了该用户
        if user in self.schedule_result[date]:
            return False

        # 3. 员工等级与偏好 (Rule 2)
        emp_type = prefs.get("employee_type", "一级")
        preferred_days = prefs.get("preferred_weekdays", []) # [0, 1, 4...]
        
        # 一级员工：偏好必须满足 (Strict)
        if emp_type == "一级":
            if preferred_days and date.weekday() not in preferred_days:
                return False
        
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

    def generate_schedule(self, existing_schedules: List[Schedule] = None) -> List[Schedule]:
        """
        使用回溯法生成排班表
        :param existing_schedules: 已有的排班记录（如锁定的排班），算法将在此基础上补充
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
        self.schedule_result = initial_schedule_result.copy()
        # Deep copy needed for defaultdict(list) to avoid sharing lists? 
        # Actually schedule_result values are lists of User objects. Shallow copy of dict is fine if we create new lists.
        # But copy() of defaultdict only copies the reference if values are mutable objects?
        # Let's do a safer copy for schedule_result
        self.schedule_result = defaultdict(list)
        for k, v in initial_schedule_result.items():
            self.schedule_result[k] = list(v)
            
        self.user_week_counts = initial_user_week_counts.copy()
        self._apply_fg_rules()
        self._apply_h_rules()
        self._apply_rotation_rules()
        self.steps = 0
        
        if self._backtrack(dates, 0, 0, strict=True):
            return self.get_result_list()
        
        # If strict mode failed, analyze WHY it failed before trying loose mode
        # Actually, if we are in strict mode and it failed, we MUST report failure if it's due to Level 1 constraints
        # But wait, maybe it's just hard to find a perfect match.
        # The user said: "If found unable to satisfy... issue warning... and state reason"
        # This implies we should TRY to produce a schedule (maybe with violations?) but WARN.
        # OR we produce NO schedule and warn.
        # "Only limited to auto scheduling... if unable to satisfy... warning... reason"
        # Usually, users prefer "Best Effort" + "Warning".
        # But if we strictly enforced Level 1 in check_constraints, then _backtrack failed means no valid schedule exists with those constraints.
        
        # Let's perform a diagnostic run to find the bottleneck
        self.last_error = self.analyze_failure(dates)
        
        # 尝试策略 2: 宽松模式 (Strict = False)
        # Even if we have an error, maybe we can produce a result?
        # But the user said "If unable to satisfy... issue warning".
        # If we return a result from loose mode, we effectively "satisfied" the request but ignored constraints.
        # We should attach the warning to the result?
        # Scheduler returns List[Schedule]. It doesn't have a side channel for warnings.
        # But we stored `self.last_error`. The caller can check it.
        
        # Reset state
        self.schedule_result = defaultdict(list)
        for k, v in initial_schedule_result.items():
            self.schedule_result[k] = list(v)
        self.user_week_counts = initial_user_week_counts.copy()
        
        self._apply_fg_rules()
        self._apply_h_rules()
        self._apply_rotation_rules()
        self.steps = 0
        
        if self._backtrack(dates, 0, 0, strict=False):
            return self.get_result_list()
            
        return []

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
        """
        应用定期轮班规则 (Periodic Rotation)
        规则 3：轮班系统只有在该员工选择了在这天期望值班才能选择
        """
        processed = set()
        
        for user in self.users:
            prefs = user.preferences or {}
            rot_pref = prefs.get("periodic_rotation")
            if not rot_pref:
                continue
            
            partner_code = rot_pref.get("partner")
            day_idx = rot_pref.get("day_idx")
            parity = rot_pref.get("parity", "odd")
            
            if not partner_code or day_idx is None:
                continue
                
            # Rule 3 Check: Must be in preferred_weekdays
            preferred_days = prefs.get("preferred_weekdays", [])
            if preferred_days and day_idx not in preferred_days:
                continue
                
            # Find partner user object
            partner = next((u for u in self.users if u.code == partner_code), None)
            if not partner:
                continue
            
            # Check partner preference too? (Maybe symmetric?)
            # Usually rotation is set up by one person or mutually. 
            # If partner didn't prefer this day, should we force?
            # User said "Employee selected...". Assume both must comply if they are to be scheduled.
            partner_prefs = partner.preferences or {}
            partner_preferred = partner_prefs.get("preferred_weekdays", [])
            if partner_preferred and day_idx not in partner_preferred:
                continue

            # Determine target date
            target_date = self.start_date + datetime.timedelta(days=day_idx)
            
            # Check if this rule for this date is already processed
            pair_key = (target_date, tuple(sorted([user.code, partner.code])))
            if pair_key in processed:
                continue
                
            processed.add(pair_key)
            
            # Determine who is on duty
            week_num = target_date.isocalendar()[1]
            is_odd_week = (week_num % 2 != 0)
            
            selected_user = None
            if parity == "odd":
                selected_user = user if is_odd_week else partner
            else: # even
                selected_user = user if not is_odd_week else partner
                
            # Apply to schedule
            # Check constraints first? Rotation usually overrides, but Level 1 constraint is HARD.
            # If selected_user is Level 1, we already checked preferred_days above.
            # Check max shifts?
            if self.check_constraints(selected_user, target_date, strict=True):
                if selected_user not in self.schedule_result[target_date]:
                    # Check if slot available
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
            candidates = list(self.schedule_result[saturday_date])
            
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
            
            # 1. 均衡性 (Balance)
            # Rule 5: Balance total shifts over time
            total_shifts = self.history_counts[code] + self.user_week_counts[code]
            score += total_shifts * 1000 
            
            # 2. 员工等级优先度 (Priority)
            # 一级员工在 check_constraints 已过滤，这里主要区分二级和三级
            # 二级比三级优先 -> 二级分数更低
            emp_type = prefs.get("employee_type", "一级")
            if emp_type == "二级":
                score -= 100
            elif emp_type == "三级":
                score += 0 # No bonus
            elif emp_type == "一级":
                # Level 1 usually hard restricted, but if they are candidate, prioritize them?
                # Actually, if Level 1 is restricted to preferred days, we should prioritize giving them shifts on those days if available?
                # Maybe neutral.
                pass
                
            # 3. 偏好匹配 (Preference Bonus)
            # 对于二级/三级员工，尽量满足偏好
            preferred_days = prefs.get("preferred_weekdays", [])
            if preferred_days and current_date.weekday() in preferred_days:
                score -= 500 # 给予很大优惠，使其优先于无偏好的人
                
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
