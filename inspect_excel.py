import pandas as pd

file_path = r"c:\Users\74927\Desktop\排班系统\项目相关资源\电力二工区人员信息 （最新）.xlsx"

try:
    df = pd.read_excel(file_path, header=1)
    print("Columns:")
    print(df.columns.tolist())
    print("\nFirst row data:")
    print(df.iloc[0])
except Exception as e:
    print(f"Error reading excel: {e}")
