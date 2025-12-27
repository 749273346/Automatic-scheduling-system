import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.orm.attributes import flag_modified
from datetime import date
from src.models import Base, User, Schedule
from src.consts import GroupType

class DBManager:
    def __init__(self, db_path="schedule.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        return self.Session()

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def init_default_users(self):
        """初始化默认用户数据 (如果数据库为空)"""
        session = self.get_session()
        if session.query(User).count() == 0:
            # 默认用户配置 (V2.0: 初始仅作为示例，后续由 SettingsView 动态控制)
            # 我们仍然保留一些初始数据以便原型演示，但不再强调分组
            colors = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD",
                "#D4A5A5", "#9B59B6", "#3498DB", "#F1C40F", "#E67E22"
            ]
            default_users = []
            for i in range(8): # Default 8 users A-H
                code = chr(65 + i) # A, B, C...
                color = colors[i % len(colors)]
                # 默认所有人都无限制，通过 preferences 控制
                # 为了兼容旧逻辑演示，暂时保留 FG/H 的特殊标记，但实际算法应优先读取 preferences
                g_type = GroupType.UNLIMITED
                prefs = {}
                
                if code in ['F', 'G']:
                    g_type = GroupType.RESTRICTED_FG
                    # V2: 将 GroupType 转换为 preferences
                    prefs = {"preferred_days": [0, 2, 4]} # Mon, Wed, Fri
                elif code == 'H':
                    g_type = GroupType.SINGLE_H
                    prefs = {"preferred_days": [1, 2, 3]} # Tue, Wed, Thu
                
                u = User(
                    code=code, 
                    name=code,
                    group_type=g_type, 
                    color=color, 
                    preferences=prefs
                )
                default_users.append(u)
                
            session.add_all(default_users)
            session.commit()
        session.close()
    
    def reset_users(self, count):
        """重置用户数量 (删除现有用户并重新生成 A-Z...)"""
        try:
            with self.session_scope() as session:
                # 清除所有排班 (因为用户ID会变)
                session.query(Schedule).delete()
                # 清除所有用户
                session.query(User).delete()
                
                colors = [
                    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD",
                    "#D4A5A5", "#9B59B6", "#3498DB", "#F1C40F", "#E67E22",
                    "#2ECC71", "#1ABC9C", "#9B59B6", "#34495E", "#16A085"
                ]
                
                new_users = []
                for i in range(count):
                    # 生成 A, B ... Z, AA, AB ...
                    if i < 26:
                        code = chr(65 + i)
                    else:
                        code = chr(65 + (i // 26) - 1) + chr(65 + (i % 26))
                    
                    color = colors[i % len(colors)]
                    u = User(
                        code=code, 
                        name=code, # Default name to code
                        group_type=GroupType.UNLIMITED, 
                        color=color, 
                        preferences={}
                    )
                    new_users.append(u)
                    
                session.add_all(new_users)
        except Exception as e:
            print(f"Error resetting users: {e}")
            raise

    def add_user(self, code, name=None, position=None, contact=None, color=None, preferences=None):
        session = self.get_session()
        try:
            # Check for unique code
            if session.query(User).filter_by(code=code).first():
                return None, "员工代码(ID)已存在"
            
            u = User(
                code=code, 
                name=name if name else code,
                position=position,
                contact=contact,
                color=color if color else "#3498DB",
                group_type=GroupType.UNLIMITED,
                is_active=True,
                preferences=preferences if preferences else {}
            )
            session.add(u)
            session.commit()
            session.refresh(u)
            session.expunge(u)
            session.close()
            return u, "成功"
        except Exception as e:
            session.rollback()
            session.close()
            return None, str(e)

    def update_user(self, user_id, **kwargs):
        session = self.get_session()
        try:
            u = session.query(User).filter_by(id=user_id).first()
            if not u:
                return False, "用户不存在"
            
            for k, v in kwargs.items():
                if hasattr(u, k):
                    setattr(u, k, v)
            
            session.commit()
            session.close()
            return True, "成功"
        except Exception as e:
            session.rollback()
            session.close()
            return False, str(e)
            
    def delete_user(self, user_id):
        # Hard delete as requested by user to allow ID reuse
        session = self.get_session()
        try:
            u = session.query(User).filter_by(id=user_id).first()
            if u:
                # 1. Delete all schedules for this user
                session.query(Schedule).filter_by(user_id=user_id).delete()
                
                # 2. Delete the user
                session.delete(u)
                
                session.commit()
            session.close()
            return True
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Delete failed: {e}")
            return False

    def clear_all_preferences(self):
        """清除所有用户的偏好设置"""
        try:
            with self.session_scope() as session:
                users = session.query(User).all()
                for user in users:
                    user.preferences = {}
                    flag_modified(user, "preferences")
            return True
        except Exception as e:
            print(f"Failed to clear preferences: {e}")
            return False

    def get_all_users(self, active_only=True):
        session = self.get_session()
        query = session.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        users = query.all()
        # Detach objects from session so they can be used after session close
        session.expunge_all() 
        session.close()
        return users

    def get_schedules_by_range(self, start_date, end_date):
        session = self.get_session()
        schedules = session.query(Schedule).options(joinedload(Schedule.user)).filter(
            Schedule.date >= start_date,
            Schedule.date <= end_date
        ).all()
        session.expunge_all()
        session.close()
        return schedules
    
    def get_all_schedules(self):
        session = self.get_session()
        schedules = session.query(Schedule).options(joinedload(Schedule.user)).all()
        session.expunge_all()
        session.close()
        return schedules

    def add_schedule(self, date_obj, user_id, is_locked=False):
        session = self.get_session()
        # 检查是否存在
        existing = session.query(Schedule).options(joinedload(Schedule.user)).filter_by(date=date_obj, user_id=user_id).first()
        if not existing:
            new_schedule = Schedule(date=date_obj, user_id=user_id, is_locked=is_locked)
            session.add(new_schedule)
            session.commit()
            session.refresh(new_schedule)
            # Eager load user
            session.query(Schedule).options(joinedload(Schedule.user)).filter_by(id=new_schedule.id).first()
            session.expunge(new_schedule)
            session.close()
            return new_schedule
        session.expunge(existing)
        session.close()
        return existing

    def delete_schedule(self, date_obj, user_id):
        session = self.get_session()
        session.query(Schedule).filter_by(date=date_obj, user_id=user_id).delete()
        session.commit()
        session.close()
        
    def save_schedules(self, schedules):
        """批量保存排班"""
        session = self.get_session()
        for sch in schedules:
            # 这里的 schedule 对象可能是 detached 的或者新建的
            # 我们根据 date 和 user_id 来判断
            existing = session.query(Schedule).filter_by(date=sch.date, user_id=sch.user_id).first()
            if not existing:
                new_sch = Schedule(date=sch.date, user_id=sch.user_id, is_locked=sch.is_locked)
                session.add(new_sch)
            else:
                existing.is_locked = sch.is_locked
        session.commit()
        session.close()

    def clear_range_schedules(self, start_date, end_date, keep_locked=True):
        session = self.get_session()
        query = session.query(Schedule).filter(
            Schedule.date >= start_date, 
            Schedule.date <= end_date
        )
        if keep_locked:
            query = query.filter(Schedule.is_locked == False)
        
        query.delete(synchronize_session=False)
        session.commit()
        session.close()

    def get_history_counts(self):
        session = self.get_session()
        # Count schedules per user
        from sqlalchemy import func
        results = session.query(User.code, func.count(Schedule.id))\
            .join(Schedule, User.id == Schedule.user_id)\
            .group_by(User.code).all()
        session.close()
        return dict(results)

    def get_last_duty_dates(self):
        """获取每个用户的最近一次排班日期"""
        session = self.get_session()
        from sqlalchemy import func
        results = session.query(User.code, func.max(Schedule.date))\
            .join(Schedule, User.id == Schedule.user_id)\
            .group_by(User.code).all()
        session.close()
        # Convert date strings/objects to date objects if needed (SQLAlchemy returns date objects for Date type)
        return dict(results)
