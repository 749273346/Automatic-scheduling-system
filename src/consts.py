from enum import Enum, auto

class GroupType(Enum):
    UNLIMITED = "UNLIMITED"  # ABCDE
    RESTRICTED_FG = "RESTRICTED_FG"  # FG: Mon, Wed, Fri
    SINGLE_H = "SINGLE_H"  # H: Tue, Wed, Thu

class WeekDay(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

# 约束常量
MAX_SHIFTS_PER_WEEK = 3
SHIFTS_PER_DAY = 2
