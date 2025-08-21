from PyQt5.QtWidgets import QAction, QMessageBox
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt
import os

class BasePlugin:
    def __init__(self):
        self.name = "未命名插件"
        self.description = "插件描述"
        self.icon = None
        self.category = "默认分类"
        
    def get_action(self, parent=None):
        """创建插件的动作"""
        # 不再保存父窗口引用
        action = QAction(self.name, parent)
        
        # 设置图标
        if self.icon:
            icon_path = os.path.join("resources", "icons", self.icon)
            if os.path.exists(icon_path):
                action.setIcon(QIcon(icon_path))
        
        # 设置工具提示和样式
        action.setToolTip(self.description)
        font = QFont()
        font.setPointSize(10)
        action.setFont(font)
        
        # 连接信号和槽
        action.triggered.connect(self.on_action_triggered)
        
        return action
    
    def on_action_triggered(self):
        """当插件动作被触发时调用"""
        # 简化处理，直接显示一个提示
        QMessageBox.information(None, "提示", f"插件 {self.name} 被点击")
        
    def get_widget(self):
        """返回插件的界面组件"""
        return None