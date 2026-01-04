import datetime
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
from src.models import User, Schedule
from src.rules_manager import RulesManager

class Scheduler:
    """
    New Weekly Scheduler based on explicit rules:
    1. Fixed assignments (User X on Monday)
    2. Rotation assignments (User X/Y rotate on Friday)
    3. Loop assignments (Fill remaining slots from a pool)
    4. Follow Saturday rule (If Sat is X, Sun is X)
    """
    def __init__(self, users: List[User], start_date: datetime.date, 
                 loop_index: int = 0, rules: Dict[str, Any] = None):
        self.users = users
        self.start_date = start_date
        self.rules = rules or RulesManager.load_rules()
        self.loop_index = loop_index
        
        # Build user map for quick lookup
        self.user_map = {u.code: u for u in self.users}
        self.user_name_map = {u.name: u for u in self.users if u.name}
        
        self.last_error = None
        self.new_loop_index = loop_index

    def _get_user(self, identifier: str) -> Optional[User]:
        if identifier in self.user_map:
            return self.user_map[identifier]
        if identifier in self.user_name_map:
            return self.user_name_map[identifier]
        return None

    def _get_consumed_slots_for_day(self, date: datetime.date) -> int:
        """Calculate how many loop pool slots are consumed on a specific date."""
        day_idx = date.weekday()
        
        # 1. Sunday Rule (Hardcoded in generate_schedule as well)
        if day_idx == 6:
            return 0
            
        # 2. Check Rule
        day_rule = self.rules.get("days", {}).get(str(day_idx), {})
        rule_type = day_rule.get("type", "loop")
        rule_users = day_rule.get("users", [])
        
        target_count = 2
        
        if rule_type == "fixed":
            # Consumes (Target - Fixed_Users_Count)
            # If 2 fixed users, consumes 0. If 0 fixed, consumes 2.
            # We assume fixed users are valid for calculation stability
            return max(0, target_count - len(rule_users))
            
        elif rule_type == "rotation":
            # Consumes 1 slot (1 rotation user + 1 loop user)
            # Unless rotation user is missing? We assume 1 is taken by rotation.
            return 1
            
        elif rule_type == "follow_saturday":
            return 0
            
        else: # loop
            return target_count

    def _calculate_anchor_loop_index(self, target_date: datetime.date) -> int:
        """
        Calculate the loop index for the target_date based on loop_start_date anchor.
        Returns: (index % pool_size)
        """
        loop_start_str = self.rules.get("loop_start_date", "")
        if not loop_start_str:
            return self.loop_index # Fallback to passed index if no anchor
            
        try:
            loop_start_date = datetime.datetime.strptime(loop_start_str, "%Y-%m-%d").date()
        except:
            return self.loop_index

        pool_codes = self.rules.get("loop_pool", [])
        # Filter valid pool
        valid_pool = [code for code in pool_codes if self._get_user(code)]
        if not valid_pool:
            return 0
            
        pool_size = len(valid_pool)
        
        # Calculate delta
        delta_slots = 0
        
        if target_date == loop_start_date:
            return 0
            
        elif target_date > loop_start_date:
            curr = loop_start_date
            while curr < target_date:
                delta_slots += self._get_consumed_slots_for_day(curr)
                curr += datetime.timedelta(days=1)
            return delta_slots % pool_size
            
        else: # target_date < loop_start_date
            curr = target_date
            while curr < loop_start_date:
                delta_slots += self._get_consumed_slots_for_day(curr)
                curr += datetime.timedelta(days=1)
            
            # If we went back X slots, index is -X
            # Python's % handles negative correctly: -1 % 5 = 4
            return (-delta_slots) % pool_size

    def generate_schedule(self, existing_schedules: List[Schedule] = None, mode: str = "all") -> List[Schedule]:
        """
        Generate schedule for the week starting at self.start_date.
        Target: 2 people per day.
        Logic: 
          1. Apply Rule (Fixed/Rotation) -> get N people.
          2. If N < 2, fill (2-N) from Loop Pool.
          3. Sunday: Copy Saturday's users exactly (no loop consumption).
        """
        result_schedules = []
        target_count = 2
        
        # Calculate Loop Start Index based on Anchor
        # This overrides self.loop_index with the strictly calculated one
        self.new_loop_index = self._calculate_anchor_loop_index(self.start_date)
        
        # Parse Loop Start Date for reference (though handled in anchor calc)
        # We don't need to reset inside the loop anymore if we calculated correctly for start_date
        # But we keep loop_start_date parsing just in case we want to verify
        
        # Pre-process existing schedules (locked slots)
        # Map: date_str -> list of user_codes
        locked_slots = defaultdict(list)
        if existing_schedules:
            for s in existing_schedules:
                if self.start_date <= s.date < self.start_date + datetime.timedelta(days=7):
                    # We respect ALL existing schedules as "locked" for simplicity in this context,
                    # or only is_locked=True. User usually expects existing DB records to hold.
                    # But for "Preview" generation, we might be overwriting.
                    # Assuming we respect them:
                    d_str = s.date.strftime("%Y-%m-%d")
                    locked_slots[d_str].append(s.user.code)

        # Determine week number for rotation
        rot_start_str = self.rules.get("rotation_start_date", "2024-01-01")
        try:
            rot_start = datetime.datetime.strptime(rot_start_str, "%Y-%m-%d").date()
        except:
            rot_start = datetime.date(2024, 1, 1)
            
        days_diff = (self.start_date - rot_start).days
        week_num = days_diff // 7
        # Week 0 (start) -> Even? Or Odd?
        # Usually "Single week" = Week 1. "Double week" = Week 2.
        # Let's map 0-indexed week_num to 1-indexed count.
        current_week_count = week_num + 1
        is_odd_week_human = (current_week_count % 2 != 0)

        # Loop Pool
        pool_codes = self.rules.get("loop_pool", [])
        valid_pool = [code for code in pool_codes if self._get_user(code)]
        
        # Store daily assignments to handle Sunday copy
        # Map: day_idx (0-6) -> list of User objects
        daily_assignments = {}

        # Iterate days
        for day_idx in range(7): # 0=Mon, 6=Sun
            current_date = self.start_date + datetime.timedelta(days=day_idx)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Note: We calculated start_index based on anchor, so we don't need manual reset here.
            # The calculation already accounted for the shift.
            
            assigned_users = []
            
            # 1. Check Locked Slots first
            if locked_slots.get(date_str):
                for u_code in locked_slots[date_str]:
                    u = self._get_user(u_code)
                    if u and u not in assigned_users:
                        assigned_users.append(u)
            
            # If already full from locks, skip rule logic
            if len(assigned_users) >= target_count:
                daily_assignments[day_idx] = assigned_users[:target_count] # Cap at target?
                # Generate schedules
                for user in daily_assignments[day_idx]:
                     result_schedules.append(Schedule(date=current_date, user_id=user.id, is_locked=True))
                continue

            # 2. Apply Rules
            # Sunday Special Rule: Copy Saturday
            if day_idx == 6: # Sunday
                # Check if "follow_saturday" is explicitly disabled? 
                # User requirement: "周六和周日的值班人员是相同的" -> Global rule implied.
                # But let's check if the user configured a specific rule for Sunday that overrides this?
                # User said: "周六和周日的值班人员是相同的，就实现这个功能".
                # So we force it.
                if 5 in daily_assignments:
                    # Copy Saturday's users
                    # But exclude any that are already locked on Sunday (unlikely but possible)
                    sat_users = daily_assignments[5]
                    for u in sat_users:
                        if u not in assigned_users and len(assigned_users) < target_count:
                            assigned_users.append(u)
            else:
                # Normal Day Rule
                day_rule = self.rules.get("days", {}).get(str(day_idx), {})
                rule_type = day_rule.get("type", "loop") # default loop implies no fixed person
                rule_users = day_rule.get("users", [])

                if rule_type == "fixed":
                    for u_code in rule_users:
                        if len(assigned_users) >= target_count: break
                        user = self._get_user(u_code)
                        if user and user not in assigned_users:
                            assigned_users.append(user)
                            
                elif rule_type == "rotation":
                    # users: [Odd, Even]
                    u_code = None
                    if len(rule_users) >= 2:
                        u_code = rule_users[0] if is_odd_week_human else rule_users[1]
                    elif len(rule_users) == 1:
                        u_code = rule_users[0]
                    
                    if u_code:
                        user = self._get_user(u_code)
                        if user and user not in assigned_users and len(assigned_users) < target_count:
                            assigned_users.append(user)
            
            # 3. Fill remaining with Loop Pool
            while len(assigned_users) < target_count:
                if not valid_pool:
                    break # No pool, can't fill
                
                # Get next from pool
                # Skip users already assigned today
                # Try finding a valid user from pool
                found_new = False
                attempts = 0
                while attempts < len(valid_pool):
                    u_code = valid_pool[self.new_loop_index % len(valid_pool)]
                    self.new_loop_index += 1
                    attempts += 1
                    
                    user = self._get_user(u_code)
                    if user and user not in assigned_users:
                        assigned_users.append(user)
                        found_new = True
                        break
                
                if not found_new:
                    # Pool exhausted or all in pool already assigned today?
                    # Stop to avoid infinite loop
                    break

            daily_assignments[day_idx] = assigned_users
            
            # Create Schedule objects
            for user in assigned_users:
                # Check if this was a locked one
                is_locked = False
                if locked_slots.get(date_str) and user.code in locked_slots[date_str]:
                    is_locked = True
                
                sch = Schedule(
                    date=current_date,
                    user_id=user.id,
                    is_locked=is_locked
                )
                sch.user = user
                result_schedules.append(sch)
                
        return result_schedules

