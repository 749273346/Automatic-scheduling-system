from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QHeaderView, QInputDialog, QColorDialog, QMessageBox, QLabel, QSpinBox, QGroupBox,
                             QDialog, QTabWidget, QCalendarWidget, QCheckBox, QComboBox, QLineEdit, QFormLayout, QDialogButtonBox, QSpacerItem, QSizePolicy,
                             QScrollArea, QGridLayout, QListWidget, QMenu, QAction, QFileDialog, QProgressDialog)
from PyQt5.QtCore import Qt, QLocale
import openpyxl
import random
from src.models import User
from src.db_manager import DBManager

class SettingsView(QWidget):
    def __init__(self, users, db_manager: DBManager, main_window):
        super().__init__()
        self.users = users
        self.db_manager = db_manager
        self.main_window = main_window # Reference to main window to update UI if needed
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("人员管理设置")
        title.setObjectName("SettingsTitle")
        layout.addWidget(title)
        
        # --- Action Bar ---
        action_layout = QHBoxLayout()
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索人员...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet("padding: 5px; border-radius: 15px; border: 1px solid #ddd;")
        self.search_input.textChanged.connect(self.load_users)
        action_layout.addWidget(self.search_input)

        action_layout.addStretch()

        # Clear Preferences Button
        self.btn_clear_prefs = QPushButton("清除所有偏好")
        self.btn_clear_prefs.setCursor(Qt.PointingHandCursor)
        self.btn_clear_prefs.clicked.connect(self.clear_all_preferences)
        self.btn_clear_prefs.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #FF3B30;
                border: 1px solid #FF3B30;
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #FFF0F0;
            }
        """)
        action_layout.addWidget(self.btn_clear_prefs)

        # Excel Import Button (New)
        self.btn_import = QPushButton(" Excel自动导入 ")
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self.import_from_excel)
        self.btn_import.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #2da84e;
            }
        """)
        action_layout.addWidget(self.btn_import)

        # Add User Button
        self.btn_add = QPushButton(" + 添加人员 ")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 6px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0069D9;
            }
        """)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_user)
        action_layout.addWidget(self.btn_add)
        
        layout.addLayout(action_layout)
        
        # --- Staff List Section ---
        layout.addSpacing(10)

        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #E5F3FF;
                color: black;
            }
        """)
        self.table.setShowGrid(False)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID (Code)", "姓名", "职位", "联系方式", "颜色", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True) # Enable sorting
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        # Empty State Label
        self.lbl_empty = QLabel("暂无人员数据，请点击右上角添加按钮")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #888; font-size: 16px; margin: 20px;")
        self.lbl_empty.setVisible(False)
        layout.addWidget(self.lbl_empty)

        # Footer Actions
        footer_layout = QHBoxLayout()
        
        self.lbl_count = QLabel()
        footer_layout.addWidget(self.lbl_count)
        
        footer_layout.addStretch()
        
        # System Reset (Kept small)
        self.btn_reset = QPushButton("系统重置")
        self.btn_reset.setFlat(True)
        self.btn_reset.setStyleSheet("color: #999; text-decoration: underline;")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_system)
        footer_layout.addWidget(self.btn_reset)
        
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.load_users)
        footer_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(footer_layout)
        
        # Initial spin count for reset logic compatibility
        self.spin_count = QSpinBox()
        self.spin_count.setValue(8) 
        self.spin_count.setVisible(False) # Hidden but kept for reset_system logic if needed

        self.load_users()

    def show_context_menu(self, pos):
        """Show context menu on right click"""
        # Get selected rows
        selected_rows = sorted(set(index.row() for index in self.table.selectionModel().selectedRows()))
        
        item = self.table.itemAt(pos)
        
        # If right-click happens on an item not in current selection, treat it as single item action
        # (unless user Ctrl+Click, but right click usually implies context of "what is under cursor" or "current selection")
        # Standard behavior: If click is inside selection, apply to selection. If outside, apply to that item (and usually select it).
        
        clicked_on_selection = False
        if item:
            if item.row() in selected_rows:
                clicked_on_selection = True
        
        menu = QMenu(self)
        
        # Batch Operation if multiple rows selected AND clicked on selection
        if len(selected_rows) > 1 and clicked_on_selection:
            delete_action = QAction(f"批量删除 ({len(selected_rows)} 人)", self)
            delete_action.triggered.connect(lambda: self.delete_selected_users(selected_rows))
            menu.addAction(delete_action)
            
        else:
            # Single item operation
            if not item:
                return
                
            row = item.row()
            user_item = self.table.item(row, 0)
            if not user_item:
                return
                
            user = user_item.data(Qt.UserRole)
            if not user:
                return
            
            delete_action = QAction("删除人员", self)
            delete_action.triggered.connect(lambda: self.delete_user(user))
            menu.addAction(delete_action)
            
            edit_action = QAction("编辑人员", self)
            edit_action.triggered.connect(lambda: self.edit_user(user))
            menu.addAction(edit_action)
            
            pref_action = QAction("偏好设置", self)
            pref_action.triggered.connect(lambda: self.edit_preferences(user))
            menu.addAction(pref_action)
            
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def delete_selected_users(self, rows):
        """Delete multiple users"""
        users_to_delete = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                user = item.data(Qt.UserRole)
                if user:
                    users_to_delete.append(user)
        
        if not users_to_delete:
            return

        names = ", ".join([u.code for u in users_to_delete[:5]])
        if len(users_to_delete) > 5:
            names += " 等"
            
        reply = QMessageBox.question(self, "确认批量删除", 
                                     f"确定要删除以下 {len(users_to_delete)} 位人员吗？\n{names}\n\n此操作不可恢复。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success_count = 0
            # Use DB transaction if possible, or just loop
            # Here we loop for simplicity as existing DBManager handles single deletes safely
            for user in users_to_delete:
                if self.db_manager.delete_user(user.id):
                    success_count += 1
            
            if success_count > 0:
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                else:
                    self.load_users() # Fallback
                QMessageBox.information(self, "成功", f"成功删除 {success_count} 位人员")
            else:
                QMessageBox.warning(self, "失败", "删除失败")

    def load_users(self):
        # Disable sorting while loading to prevent artifacts
        self.table.setSortingEnabled(False)
        
        search_text = self.search_input.text().strip().lower()
        filtered_users = []
        for u in self.users:
            # Filter logic
            if search_text:
                if (search_text not in u.code.lower() and 
                    search_text not in (u.name or "").lower() and 
                    search_text not in (u.position or "").lower()):
                    continue
            filtered_users.append(u)
            
        self.table.setRowCount(0)
        self.lbl_count.setText(f"显示 {len(filtered_users)} / {len(self.users)} 人")
        
        if not filtered_users:
            self.table.setVisible(False)
            self.lbl_empty.setVisible(True)
            if search_text:
                self.lbl_empty.setText("未找到匹配的人员")
            else:
                self.lbl_empty.setText("暂无人员数据，请点击右上角添加按钮")
        else:
            self.table.setVisible(True)
            self.lbl_empty.setVisible(False)
        
        for row, user in enumerate(filtered_users):
            self.table.insertRow(row)
            
            # ID
            item_code = QTableWidgetItem(user.code)
            item_code.setTextAlignment(Qt.AlignCenter)
            item_code.setData(Qt.UserRole, user) # Store user object if needed
            self.table.setItem(row, 0, item_code)
            
            # Name
            item_name = QTableWidgetItem(user.name or "")
            item_name.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item_name)
            
            # Position
            item_pos = QTableWidgetItem(user.position or "-")
            item_pos.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_pos)
            
            # Contact
            item_contact = QTableWidgetItem(user.contact or "-")
            item_contact.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_contact)

            # Color
            btn_color = QPushButton()
            btn_color.setStyleSheet(f"background-color: {user.color}; border: 1px solid #ddd; border-radius: 4px;")
            btn_color.setCursor(Qt.PointingHandCursor)
            btn_color.clicked.connect(lambda checked, u=user: self.change_color(u))
            btn_color.setFixedSize(60, 20)
            
            # Center widget in cell
            color_container = QWidget()
            color_layout = QHBoxLayout(color_container)
            color_layout.setContentsMargins(0, 0, 0, 0)
            color_layout.setAlignment(Qt.AlignCenter)
            color_layout.addWidget(btn_color)
            self.table.setCellWidget(row, 4, color_container)

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 2, 0, 2)
            action_layout.setAlignment(Qt.AlignCenter)
            
            btn_edit = QPushButton("编辑")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setStyleSheet("color: #007AFF; border: none; font-weight: bold;")
            btn_edit.clicked.connect(lambda checked, u=user: self.edit_user(u))
            action_layout.addWidget(btn_edit)
            
            btn_pref = QPushButton("偏好")
            btn_pref.setCursor(Qt.PointingHandCursor)
            btn_pref.setStyleSheet("color: #5856D6; border: none;")
            btn_pref.clicked.connect(lambda checked, u=user: self.edit_preferences(u))
            action_layout.addWidget(btn_pref)
            
            btn_del = QPushButton("删除")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("color: #FF3B30; border: none;")
            btn_del.clicked.connect(lambda checked, u=user: self.delete_user(u))
            action_layout.addWidget(btn_del)
            
            self.table.setCellWidget(row, 5, action_widget)
            
        self.table.setSortingEnabled(True) # Re-enable sorting
    
    def clear_all_preferences(self):
        reply = QMessageBox.question(
            self, 
            "确认清除", 
            "确定要清除所有人员的偏好设置吗？\n此操作将重置所有人的排班偏好（如不可排班日期、偏好工作日等）。\n\n注意：此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.clear_all_preferences():
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                else:
                    self.users = self.db_manager.get_all_users()
                    self.load_users()
                QMessageBox.information(self, "成功", "所有偏好设置已清除。")
            else:
                QMessageBox.warning(self, "失败", "清除偏好设置失败，请重试。")

    def import_from_excel(self):
        """Import users from Excel file with smart column recognition"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择人员信息表", "", "Excel Files (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
            
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            
            # 1. Identify Header Row
            header_row_idx = None
            column_map = {}
            
            # Keywords for column mapping
            keywords = {
                'code': ['id', 'code', '编号', '工号', '代码'],
                'name': ['姓名', '名字', 'name'],
                'position': ['职务', '职位', '岗位', 'role', 'position'],
                'contact': ['联系方式', '电话', '手机', 'contact', 'phone', 'tel'],
                'color': ['颜色', 'color'],
                'priority': ['优先等级', '等级', '员工类型', 'priority', 'level', 'type']
            }
            
            # Scan first 10 rows for headers
            for r in range(1, min(11, sheet.max_row + 1)):
                row_values = [str(sheet.cell(row=r, column=c).value or "").strip().lower() for c in range(1, sheet.max_column + 1)]
                
                # Check if this row looks like a header (contains at least 'name' or 'code')
                matches = 0
                temp_map = {}
                
                for col_idx, cell_val in enumerate(row_values):
                    # Check against keywords
                    for key, words in keywords.items():
                        if any(w in cell_val for w in words):
                            temp_map[key] = col_idx + 1 # 1-based column index
                            break
                            
                if 'name' in temp_map or 'code' in temp_map:
                    if len(temp_map) >= 2: # At least 2 columns matched
                        header_row_idx = r
                        column_map = temp_map
                        break
            
            if not header_row_idx:
                QMessageBox.warning(self, "识别失败", "无法识别表头，请确保表格包含'姓名'、'工号'等列名。")
                return
                
            # 2. Process Data Rows
            success_count = 0
            fail_count = 0
            errors = []
            
            # Pre-fetch existing codes to avoid duplicates
            existing_codes = {u.code.strip().upper() for u in self.db_manager.get_all_users()}
            
            # Pre-scan Excel for explicit codes to ensure generator doesn't conflict
            excel_explicit_codes = set()
            for r in range(header_row_idx + 1, sheet.max_row + 1):
                if 'code' in column_map:
                    val = sheet.cell(row=r, column=column_map['code']).value
                    if val:
                        code_str = str(val).strip().upper()
                        if code_str:
                            excel_explicit_codes.add(code_str)
                            
            used_codes = existing_codes.union(excel_explicit_codes)
            
            # Helper to generate random color
            def generate_random_color():
                """Generate a random pleasing color"""
                # Generate RGB values ensuring they aren't too dark or too light
                r = random.randint(60, 220)
                g = random.randint(60, 220)
                b = random.randint(60, 220)
                return f"#{r:02X}{g:02X}{b:02X}"

            # Helper to generate next available code
            def generate_next_code():
                # Try single letters A-Z
                for i in range(26):
                    c = chr(65 + i)
                    if c not in used_codes:
                        used_codes.add(c)
                        return c
                # Try double letters AA-ZZ
                for i in range(26):
                    for j in range(26):
                        c = chr(65 + i) + chr(65 + j)
                        if c not in used_codes:
                            used_codes.add(c)
                            return c
                # Fallback numeric
                idx = 1
                while True:
                    c = f"U{idx}"
                    if c not in used_codes:
                        used_codes.add(c)
                        return c
                    idx += 1
            
            # Progress Dialog
            progress = QProgressDialog("正在导入数据...", "取消", 0, sheet.max_row - header_row_idx, self)
            progress.setWindowModality(Qt.WindowModal)
            
            for i, r in enumerate(range(header_row_idx + 1, sheet.max_row + 1)):
                if progress.wasCanceled():
                    break
                
                progress.setValue(i)
                
                # Extract values
                def get_val(key):
                    if key in column_map:
                        val = sheet.cell(row=r, column=column_map[key]).value
                        return str(val).strip() if val is not None else None
                    return None
                
                code = get_val('code')
                name = get_val('name')
                
                # Skip empty rows (neither name nor code)
                if not code and not name:
                    continue
                    
                # Auto-generate ID if missing
                if not code:
                     code = generate_next_code()
                     # If name is also missing (should be caught above), but double check
                     if not name:
                         name = f"员工{code}"
                
                position = get_val('position')
                contact = get_val('contact')
                color = get_val('color')
                if not color:
                    color = generate_random_color()
                priority_val = get_val('priority')
                
                # Parse priority
                prefs = {}
                if priority_val:
                    if "一" in priority_val or "1" in priority_val:
                        prefs["employee_type"] = "一级"
                    elif "二" in priority_val or "2" in priority_val:
                        prefs["employee_type"] = "二级"
                    elif "三" in priority_val or "3" in priority_val:
                        prefs["employee_type"] = "三级"
                    else:
                         prefs["employee_type"] = "一级" # Default
                
                # Add to DB
                user, msg = self.db_manager.add_user(
                    code=code,
                    name=name,
                    position=position,
                    contact=contact,
                    color=color,
                    preferences=prefs
                )
                
                if user:
                    success_count += 1
                else:
                    # If it failed because ID exists, maybe update?
                    # "员工代码(ID)已存在"
                    if "存在" in msg:
                        # Update logic could go here if requested
                        # For now, just report error
                        fail_count += 1
                        errors.append(f"行 {r} ({name}): {msg}")
                    else:
                        fail_count += 1
                        errors.append(f"行 {r} ({name}): {msg}")
            
            progress.setValue(sheet.max_row - header_row_idx)
            
            # Reload UI
            self.users = self.db_manager.get_all_users()
            self.load_users()
            if hasattr(self.main_window, 'reload_data'):
                self.main_window.reload_data()
                
            # Report
            if fail_count == 0:
                QMessageBox.information(self, "导入完成", f"成功导入 {success_count} 条数据。")
            else:
                err_msg = "\n".join(errors[:10])
                if len(errors) > 10:
                    err_msg += "\n..."
                QMessageBox.warning(self, "导入完成 (有错误)", f"成功: {success_count}\n失败: {fail_count}\n\n错误详情:\n{err_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"读取文件时发生错误: {str(e)}")

    def add_user(self):
        dialog = UserEditDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # Prepare preferences
            prefs = {}
            if "employee_type" in data:
                prefs["employee_type"] = data["employee_type"]

            user, msg = self.db_manager.add_user(
                code=data['code'],
                name=data['name'],
                position=data['position'],
                contact=data['contact'],
                color=data['color'],
                preferences=prefs
            )
            if user:
                # Refresh data
                self.users.append(user)
                self.load_users()
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                QMessageBox.information(self, "成功", "人员添加成功")
            else:
                QMessageBox.warning(self, "失败", f"添加失败: {msg}")

    def edit_user(self, user):
        dialog = UserEditDialog(user, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # Prepare preferences update
            current_prefs = dict(user.preferences) if user.preferences else {}
            current_prefs["employee_type"] = data.get("employee_type", "一级")
            
            # Code is usually immutable or needs check
            # Update DB
            success, msg = self.db_manager.update_user(
                user.id,
                name=data['name'],
                position=data['position'],
                contact=data['contact'],
                color=data['color'],
                preferences=current_prefs
            )
            if success:
                # Update memory
                user.name = data['name']
                user.position = data['position']
                user.contact = data['contact']
                user.color = data['color']
                user.preferences = current_prefs
                self.load_users()
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                QMessageBox.information(self, "成功", "人员信息已更新\n\n注意：修改仅影响后续自动排班，现有排班记录不会改变。")
            else:
                QMessageBox.warning(self, "失败", f"更新失败: {msg}")

    def delete_user(self, user):
        reply = QMessageBox.question(self, "确认删除", 
                                     f"确定要删除人员 {user.name or user.code} 吗？\n此操作不可恢复。\n\n注意：删除后，该人员的历史排班记录将保留，但不会再参与新的排班。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_user(user.id):
                self.users = [u for u in self.users if u.id != user.id]
                self.load_users()
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                QMessageBox.information(self, "成功", "人员已删除")
            else:
                QMessageBox.warning(self, "失败", "删除失败")


    def change_color(self, user):
        color = QColorDialog.getColor(initial=Qt.white, parent=self, title=f"选择 {user.code} 的颜色")
        if color.isValid():
            new_color = color.name()
            # Update DB
            session = self.db_manager.get_session()
            db_user = session.query(User).filter_by(id=user.id).first()
            if db_user:
                db_user.color = new_color
                session.commit()
                # Update memory object
                user.color = new_color
                # Refresh UI
                self.load_users()
                if hasattr(self.main_window, 'reload_data'):
                    self.main_window.reload_data()
                QMessageBox.information(self, "成功", "颜色已更新")
            session.close()

    def edit_preferences(self, user):
        dialog = PreferenceDialog(user, self.users, self)
        if dialog.exec_() == QDialog.Accepted:
            new_prefs = dialog.get_preferences()
            
            # Update DB
            session = self.db_manager.get_session()
            db_user = session.query(User).filter_by(id=user.id).first()
            if db_user:
                db_user.preferences = new_prefs
                # Force SQLAlchemy to detect change in JSON column
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(db_user, "preferences")
                
                session.commit()
                
                # Update memory object
                user.preferences = new_prefs
                
                QMessageBox.information(self, "成功", "偏好设置已保存\n\n注意：新的偏好设置将仅应用于后续生成的排班，现有排班不会受影响。")
            session.close()

    def reset_system(self):
        count = self.spin_count.value()
        reply = QMessageBox.question(self, "确认重置", 
                                     f"确定要重置系统为 {count} 人吗？\n警告：这将清空所有现有的排班记录！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.reset_users(count)
                # Refresh Main Window Data
                self.main_window.reload_data()
                QMessageBox.information(self, "重置成功", f"系统已重置为 {count} 人。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置失败: {str(e)}")

    def update_data(self, users):
        self.users = users
        self.spin_count.setValue(len(users))
        self.load_users()


class PreferenceDialog(QDialog):
    def __init__(self, user, all_users, parent=None):
        super().__init__(parent)
        self.user = user
        self.all_users = all_users
        self.preferences = dict(user.preferences) if user.preferences else {}
        
        self.setWindowTitle(f"偏好设置 - {user.code}")
        self.resize(600, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Preferences (Cycle & Pairing)
        self.tab_advanced = QWidget()
        self.init_advanced_tab()
        tabs.addTab(self.tab_advanced, "高级偏好")

        # Tab 2: Blackout Dates
        self.tab_dates = QWidget()
        self.init_dates_tab()
        tabs.addTab(self.tab_dates, "不可值班日期")
        
        # Default to Advanced Preferences (Index 0)
        tabs.setCurrentIndex(0)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
    def init_dates_tab(self):
        layout = QVBoxLayout(self.tab_dates)
        
        lbl = QLabel("选择该人员无法值班的日期（点击日期切换选中状态）:")
        layout.addWidget(lbl)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.toggle_date)
        layout.addWidget(self.calendar)
        
        lbl_hint = QLabel("已选日期 (右键点击列表项可删除):")
        layout.addWidget(lbl_hint)

        self.list_dates = QListWidget()
        self.list_dates.setFixedHeight(100)
        self.list_dates.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_dates.customContextMenuRequested.connect(self.show_date_context_menu)
        layout.addWidget(self.list_dates)
        
        # Load existing blackout dates
        self.blackout_dates = set(self.preferences.get("blackout_dates", []))
        self.update_date_list()
        
    def toggle_date(self, date):
        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.blackout_dates:
            self.blackout_dates.remove(date_str)
        else:
            self.blackout_dates.add(date_str)
        self.update_date_list()
        
    def update_date_list(self):
        self.list_dates.clear()
        if not self.blackout_dates:
            self.list_dates.addItem("无")
            self.list_dates.setEnabled(False)
        else:
            self.list_dates.setEnabled(True)
            sorted_dates = sorted(list(self.blackout_dates))
            for date_str in sorted_dates:
                self.list_dates.addItem(date_str)

    def show_date_context_menu(self, position):
        item = self.list_dates.itemAt(position)
        if not item or item.text() == "无":
            return
            
        menu = QMenu()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_selected_date(item))
        menu.addAction(delete_action)
        menu.exec_(self.list_dates.mapToGlobal(position))
        
    def delete_selected_date(self, item):
        date_str = item.text()
        if date_str in self.blackout_dates:
            self.blackout_dates.remove(date_str)
            self.update_date_list()
            
    def init_advanced_tab(self):
        layout = QVBoxLayout(self.tab_advanced)
        
        # 1. Preferred Weekdays (期望周几值班)
        grp_weekdays = QGroupBox("1. 期望值班日 (每周)")
        weekdays_layout = QHBoxLayout(grp_weekdays)
        self.weekday_checks = []
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        preferred_days = self.preferences.get("preferred_weekdays", [])
        
        for i, day in enumerate(days):
            chk = QCheckBox(day)
            if i in preferred_days:
                chk.setChecked(True)
            self.weekday_checks.append(chk)
            weekdays_layout.addWidget(chk)
            
        layout.addWidget(grp_weekdays)

        # 2. Cycle Preference (值班周期)
        grp_cycle = QGroupBox("2. 偏好值班周期")
        cycle_layout = QVBoxLayout(grp_cycle)
        self.combo_cycle = QComboBox()
        self.combo_cycle.addItems(["无特定偏好", "每周", "每两周 (隔周)", "每月"])
        
        # Load existing cycle
        current_cycle = self.preferences.get("preferred_cycle", "无特定偏好")
        index = self.combo_cycle.findText(current_cycle)
        if index >= 0:
            self.combo_cycle.setCurrentIndex(index)
            
        cycle_layout.addWidget(self.combo_cycle)
        layout.addWidget(grp_cycle)

        # 3. Avoid Holidays (不期望在哪个法定节假日值班)
        grp_holiday = QGroupBox("3. 不期望值班的节假日")
        holiday_layout = QGridLayout(grp_holiday)
        self.holiday_checks = {}
        holidays = ["元旦", "春节", "清明节", "劳动节", "端午节", "中秋节", "国庆节"]
        avoid_holidays = set(self.preferences.get("avoid_holidays", []))
        
        for i, h_name in enumerate(holidays):
            chk = QCheckBox(h_name)
            if h_name in avoid_holidays:
                chk.setChecked(True)
            self.holiday_checks[h_name] = chk
            holiday_layout.addWidget(chk, i // 4, i % 4)
            
        layout.addWidget(grp_holiday)
        
        # 4. Periodic Rotation (定期轮班)
        grp_rotation = QGroupBox("4. 定期轮班 (与他人轮流值班)")
        rotation_layout = QFormLayout(grp_rotation)
        
        # Load existing rotation preference
        # Structure: {"partner": "CODE", "day_idx": 4, "parity": "odd"} 
        # parity: "odd" (1,3,5...) or "even" (2,4,6...)
        rotation_pref = self.preferences.get("periodic_rotation", {})
        
        # Partner Selector
        self.combo_rotation_partner = QComboBox()
        self.combo_rotation_partner.addItem("无 (不启用)", None)
        
        current_partner_code = rotation_pref.get("partner")
        
        sorted_users = sorted(self.all_users, key=lambda u: u.code)
        for u in sorted_users:
            if u.id == self.user.id:
                continue
            self.combo_rotation_partner.addItem(f"{u.code} ({u.name or ''})", u.code)
            
        if current_partner_code:
            idx = self.combo_rotation_partner.findData(current_partner_code)
            if idx >= 0:
                self.combo_rotation_partner.setCurrentIndex(idx)
                
        rotation_layout.addRow("轮班搭档:", self.combo_rotation_partner)
        
        # Day Selector
        self.combo_rotation_day = QComboBox()
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.combo_rotation_day.addItems(days)
        
        current_day = rotation_pref.get("day_idx", 4) # Default Friday
        if 0 <= current_day <= 6:
            self.combo_rotation_day.setCurrentIndex(current_day)
            
        rotation_layout.addRow("轮班星期:", self.combo_rotation_day)
        
        # Parity Selector
        self.combo_rotation_parity = QComboBox()
        # odd = week 1, 3, 5...; even = week 2, 4, 6...
        self.combo_rotation_parity.addItem("单周值班 (第1, 3, 5...周)", "odd")
        self.combo_rotation_parity.addItem("双周值班 (第2, 4, 6...周)", "even")
        
        current_parity = rotation_pref.get("parity", "odd")
        idx_parity = self.combo_rotation_parity.findData(current_parity)
        if idx_parity >= 0:
            self.combo_rotation_parity.setCurrentIndex(idx_parity)
            
        rotation_layout.addRow("我的班次:", self.combo_rotation_parity)
        
        # Explanation
        lbl_rot_hint = QLabel("说明：设置后，您将与搭档在指定星期轮流值班。\n请确保搭档未设置冲突的轮班规则。")
        lbl_rot_hint.setStyleSheet("color: gray; font-size: 11px;")
        rotation_layout.addRow(lbl_rot_hint)
        
        layout.addWidget(grp_rotation)
        
        layout.addStretch()

    def get_preferences(self):
        prefs = self.preferences.copy()
        prefs["blackout_dates"] = sorted(list(self.blackout_dates))
        
        # 1. Weekdays
        weekdays = []
        for i, chk in enumerate(self.weekday_checks):
            if chk.isChecked():
                weekdays.append(i)
        prefs["preferred_weekdays"] = weekdays
        
        # 2. Cycle
        prefs["preferred_cycle"] = self.combo_cycle.currentText()
        
        # 3. Holidays
        holidays = []
        for name, chk in self.holiday_checks.items():
            if chk.isChecked():
                holidays.append(name)
        prefs["avoid_holidays"] = holidays
        
        # 4. Periodic Rotation
        partner_code = self.combo_rotation_partner.currentData()
        if partner_code:
            prefs["periodic_rotation"] = {
                "partner": partner_code,
                "day_idx": self.combo_rotation_day.currentIndex(),
                "parity": self.combo_rotation_parity.currentData()
            }
        else:
            # If "None" is selected, remove the key if it exists
            if "periodic_rotation" in prefs:
                del prefs["periodic_rotation"]
        
        # Remove legacy pairing key if it exists, as UI is gone
        if "avoid_pairing" in prefs:
            del prefs["avoid_pairing"]
            
        return prefs

class UserEditDialog(QDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("编辑人员" if user else "添加人员")
        self.setFixedWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # ID/Code
        self.edit_code = QLineEdit()
        if self.user:
            self.edit_code.setText(self.user.code)
            self.edit_code.setReadOnly(True) # Code is unique ID, usually not editable after creation
            self.edit_code.setPlaceholderText("系统自动生成或手动输入")
        else:
            self.edit_code.setPlaceholderText("必填，唯一标识 (如 A, B, 001)")
            
        form_layout.addRow("员工ID/代码:", self.edit_code)
        
        # Name
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("必填，显示名称")
        if self.user:
            self.edit_name.setText(self.user.name or self.user.code)
        form_layout.addRow("姓名:", self.edit_name)
        
        # Position
        self.combo_position = QComboBox()
        self.combo_position.addItems(["工长", "副工长", "职工", "见习生"])
        self.combo_position.setEditable(True) # Allow custom
        if self.user and self.user.position:
            self.combo_position.setCurrentText(self.user.position)
        form_layout.addRow("职务:", self.combo_position)
        
        # Contact
        self.edit_contact = QLineEdit()
        if self.user and self.user.contact:
            self.edit_contact.setText(self.user.contact)
        form_layout.addRow("联系方式:", self.edit_contact)
        
        # Priority Level (formerly Employee Type)
        self.combo_employee_type = QComboBox()
        self.combo_employee_type.addItems(["一级", "二级", "三级"])
        current_type = "一级"
        if self.user and self.user.preferences:
            # Fallback to check permission_level if employee_type not set (migration support)
            raw_type = self.user.preferences.get("employee_type", "一级")
            # Map legacy values to new values
            mapping = {"一类": "一级", "二类": "二级", "三类": "三级"}
            current_type = mapping.get(raw_type, raw_type)
            
        self.combo_employee_type.setCurrentText(current_type)
        form_layout.addRow("优先等级:", self.combo_employee_type)
        
        # Color
        self.btn_color = QPushButton()
        self.current_color = self.user.color if self.user else "#3498DB"
        self.btn_color.setStyleSheet(f"background-color: {self.current_color}; border: none; border-radius: 4px;")
        self.btn_color.setFixedHeight(25)
        self.btn_color.clicked.connect(self.choose_color)
        form_layout.addRow("代表颜色:", self.btn_color)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setText("保存")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def choose_color(self):
        color = QColorDialog.getColor(initial=Qt.white, parent=self, title="选择颜色")
        if color.isValid():
            self.current_color = color.name()
            self.btn_color.setStyleSheet(f"background-color: {self.current_color}; border: none; border-radius: 4px;")
            
    def validate_and_accept(self):
        if not self.edit_code.text().strip():
            QMessageBox.warning(self, "验证失败", "员工ID/代码不能为空")
            return
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "验证失败", "姓名不能为空")
            return
        self.accept()
        
    def get_data(self):
        return {
            "code": self.edit_code.text().strip(),
            "name": self.edit_name.text().strip(),
            "position": self.combo_position.currentText().strip(),
            "contact": self.edit_contact.text().strip(),
            "color": self.current_color,
            "employee_type": self.combo_employee_type.currentText()
        }
