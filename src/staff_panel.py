from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                             QListWidgetItem, QFrame)
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

class StaffListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
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
        pixmap = QPixmap(100, 30)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        
        # Use user's specific color
        bg_color = QColor(item.user.color) if item.user.color else QColor("#007AFF")
        painter.setBrush(bg_color)
        
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 100, 30, 5, 5)
        painter.setPen(Qt.white)
        display_text = item.user.name if item.user.name else item.user.code
        painter.drawText(pixmap.rect(), Qt.AlignCenter, display_text)
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        drag.exec_(Qt.CopyAction)

class StaffPanel(QWidget):
    def __init__(self, users):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("人员列表 (可拖拽)")
        title.setStyleSheet("font-weight: 600; color: #1D1D1F; font-size: 16px; margin-bottom: 8px;")
        self.layout.addWidget(title)
        
        self.list_widget = StaffListWidget()
        # Increase font size and item padding
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
            }
        """)
        self.layout.addWidget(self.list_widget)
        
        self.refresh_list(users)
        
    def refresh_list(self, users):
        self.list_widget.clear()
        for user in users:
            item = DraggableUserItem(user)
            self.list_widget.addItem(item)
