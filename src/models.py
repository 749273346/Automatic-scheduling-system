from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship
from src.consts import GroupType

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)  # A, B, C...
    # group_type is kept for backward compatibility or simple preset rules, 
    # but we will rely more on 'preferences' for the new flexible system.
    group_type = Column(SQLEnum(GroupType), nullable=True, default=GroupType.UNLIMITED)
    color = Column(String, default="#FFFFFF")
    
    # Store flexible preferences:
    # {
    #   "blackout_dates": ["2023-01-01", ...],
    #   "preferred_days": [0, 1, ...], # 0=Mon
    #   "pairing_preference": {"avoid": ["B"], "prefer": ["C"]}
    # }
    preferences = Column(JSON, default=dict)

    # V2.1 Enhanced fields
    name = Column(String, nullable=True) # Display name
    position = Column(String, nullable=True) # Job title/Role
    contact = Column(String, nullable=True) # Phone/Email
    is_active = Column(Boolean, default=True) # For soft delete

    # 运行时属性，不存储在数据库中
    current_week_shifts = 0

    def __repr__(self):
        return f"<User(code={self.code})>"

class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_locked = Column(Boolean, default=False)
    
    user = relationship("User")

    def __repr__(self):
        return f"<Schedule(date={self.date}, user={self.user.code})>"
