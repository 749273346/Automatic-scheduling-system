import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db_manager import DBManager
from src.models import User, Schedule
from src.consts import GroupType

def generate_code(index):
    """Generate code like A, B... Z, AA, AB..."""
    if index < 26:
        return chr(65 + index)
    else:
        return chr(65 + (index // 26) - 1) + chr(65 + (index % 26))

def import_data():
    file_path = r"c:\Users\74927\Desktop\排班系统\项目相关资源\电力二工区人员信息 （最新）.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        # Header=1 implies the second row (index 1) is the header
        df = pd.read_excel(file_path, header=1)
        print("Excel loaded successfully.")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading excel: {e}")
        return

    db = DBManager()
    
    # Pre-defined colors
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD",
        "#D4A5A5", "#9B59B6", "#3498DB", "#F1C40F", "#E67E22",
        "#2ECC71", "#1ABC9C", "#9B59B6", "#34495E", "#16A085"
    ]

    with db.session_scope() as session:
        # Clear existing data
        print("Clearing existing database...")
        session.query(Schedule).delete()
        session.query(User).delete()
        
        users_to_add = []
        count = 0
        
        for index, row in df.iterrows():
            # Check if name is valid (not NaN)
            if pd.isna(row.get('姓名')):
                continue
                
            name = str(row.get('姓名', '')).strip()
            position = str(row.get('职务', '')).strip() if not pd.isna(row.get('职务')) else ""
            contact = str(row.get('电话号码', '')).strip() if not pd.isna(row.get('电话号码')) else ""
            
            code = generate_code(count)
            color = colors[count % len(colors)]
            
            user = User(
                code=code,
                name=name,
                position=position,
                contact=contact,
                color=color,
                group_type=GroupType.UNLIMITED, # Default
                preferences={},
                is_active=True
            )
            users_to_add.append(user)
            count += 1
            print(f"Prepared user: {name} ({code}) - {position}")

        if users_to_add:
            session.add_all(users_to_add)
            print(f"Successfully imported {len(users_to_add)} users.")
        else:
            print("No users found to import.")

if __name__ == "__main__":
    import_data()
