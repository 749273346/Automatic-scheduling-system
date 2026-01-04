from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                             QListWidgetItem, QFrame, QMenu, QAction, QMessageBox, QPushButton)
from PyQt5.QtCore import Qt, QMimeData, QSize
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor

from src.models import User
from src.consts import GroupType

class DraggableUserItem(QListWidgetItem):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        display_name = user.name if user.name else "未命名"
        self.setText(f"{user.code}: {display_name}")
        self.setToolTip(f"人员: {user.code} - {display_name}")
        # self.setTextAlignment(Qt.AlignCenter) # Reverted to left alignment as requested

class StaffListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        # Styles moved to resources/style.qss

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        # 传递 user_id 和 user_code
        mime_data.setText(f"{item.user.id},{item.user.code},{item.user.group_type.name}") 
        drag.setMimeData(mime_data)
        
        # 创建拖拽时的视觉反馈
        pixmap = QPixmap(140, 36)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        
        # Use user's specific color
        bg_color = QColor(item.user.color) if item.user.color else QColor("#007AFF")
        painter.setBrush(bg_color)
        
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 140, 36, 6, 6)
        painter.setPen(Qt.white)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        
        display_text = item.user.name if item.user.name else item.user.code
        painter.drawText(pixmap.rect(), Qt.AlignCenter, display_text)
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        drag.exec_(Qt.CopyAction)

class StaffPanel(QWidget):
    def __init__(self, users, db_manager=None, reload_callback=None):
        super().__init__()
        self.db_manager = db_manager
        self.reload_callback = reload_callback
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("人员列表 (可拖拽)")
        title.setStyleSheet("font-weight: 600; color: #1D1D1F; font-size: 16px; margin-bottom: 8px;")
        self.layout.addWidget(title)
        
        self.list_widget = StaffListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F5F5F7;
            }
            QListWidget::item:selected {
                background-color: #E5F1FB;
                color: #007AFF;
            }
        """)
        self.layout.addWidget(self.list_widget)
        
        # Delete Button
        self.btn_delete = QPushButton("🗑️ 删除选中人员")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #FF3B30;
                border: 1px solid #FF3B30;
                border-radius: 8px;
                padding: 8px;
                font-weight: 600;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #FFF0F0;
            }
        """)
        self.btn_delete.clicked.connect(self.delete_selected_users)
        self.layout.addWidget(self.btn_delete)
        
        self.refresh_list(users)

    def refresh_list(self, users):
        self.list_widget.clear()
        for user in users:
            item = DraggableUserItem(user)
            self.list_widget.addItem(item)

    def show_context_menu(self, pos):
        if not self.db_manager: return

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        
        # Win11 Style Menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 6px;
                color: #333;
                font-size: 13px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #F2F2F7;
                color: #000;
            }
        """)
        
        action_del = QAction(f"🗑️ 删除选中 ({len(selected_items)})", self)
        action_del.triggered.connect(self.delete_selected_users)
        menu.addAction(action_del)
        
        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    def delete_selected_users(self):
        if not self.db_manager: return
        
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        
        names = [item.user.name for item in selected_items]
        count = len(names)
        
        msg = f"确定要删除选中的 {count} 名人员吗？\n\n"
        if count <= 5:
            msg += "、".join(names)
        else:
            msg += "、".join(names[:5]) + " 等..."
            
        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success_count = 0
            for item in selected_items:
                if self.db_manager.delete_user(item.user.id):
                    success_count += 1
            
            if self.reload_callback:
                self.reload_callback()
            else:
                # Fallback if no callback, just remove from list (but main data might be stale)
                for item in selected_items:
                    row = self.list_widget.row(item)
                    self.list_widget.takeItem(row)
            
            QMessageBox.information(self, "成功", f"成功删除 {success_count} 名人员。")
