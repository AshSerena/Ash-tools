import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame, QListWidget, QListWidgetItem, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from core.plugin_manager import PluginManager


class OfficeToolsTab(QWidget):
    """办公工具标签页 - 作为主窗口的固定标签页"""
    def __init__(self, plugin_manager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.current_plugin = None
        self.init_ui()
    
    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建插件列表和插件显示区域的分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建插件列表区域
        plugin_list_widget = QWidget()
        plugin_list_layout = QVBoxLayout(plugin_list_widget)
        
        # 创建插件列表
        self.plugin_list = QListWidget()
        self.plugin_list.setAlternatingRowColors(True)
        self.plugin_list.itemClicked.connect(self.show_plugin)
        
        # 加载办公工具插件
        self.load_office_plugins()
        
        plugin_list_layout.addWidget(QLabel("选择工具:"))
        plugin_list_layout.addWidget(self.plugin_list)
        
        # 创建插件显示区域
        self.plugin_display = QStackedWidget()
        
        # 添加默认提示页面
        self.default_widget = self.create_default_widget()
        self.plugin_display.addWidget(self.default_widget)
        self.plugin_display.setCurrentWidget(self.default_widget)
        
        # 添加分割器到主布局
        splitter.addWidget(plugin_list_widget)
        splitter.addWidget(self.plugin_display)
        splitter.setSizes([200, 800])  # 设置分割比例
        
        main_layout.addWidget(splitter)
    
    def load_office_plugins(self):
        # 清空插件列表
        self.plugin_list.clear()
        
        # 加载所有办公工具插件
        for plugin in self.plugin_manager.plugins:
            if hasattr(plugin, 'category') and plugin.category == "办公工具":
                item = QListWidgetItem(plugin.name)
                if hasattr(plugin, 'description'):
                    item.setToolTip(plugin.description)
                self.plugin_list.addItem(item)
    
    def show_plugin(self, item):
        # 获取选中的插件
        plugin_name = item.text()
        
        # 查找对应的插件
        selected_plugin = None
        for plugin in self.plugin_manager.plugins:
            if hasattr(plugin, 'category') and plugin.category == "办公工具" and plugin.name == plugin_name:
                selected_plugin = plugin
                break
        
        if selected_plugin:
            self.current_plugin = selected_plugin
            
            # 检查插件是否已经加载
            plugin_loaded = False
            for i in range(self.plugin_display.count()):
                widget = self.plugin_display.widget(i)
                if hasattr(widget, 'plugin_name') and widget.plugin_name == plugin_name:
                    self.plugin_display.setCurrentIndex(i)
                    plugin_loaded = True
                    break
            
            # 如果未加载，则创建插件界面
            if not plugin_loaded:
                try:
                    plugin_widget = selected_plugin.get_widget()
                    if plugin_widget:
                        plugin_widget.plugin_name = plugin_name
                        self.plugin_display.addWidget(plugin_widget)
                        self.plugin_display.setCurrentWidget(plugin_widget)
                    else:
                        print(f"无法加载插件界面: {plugin_name}")
                except Exception as e:
                    print(f"加载插件时出错: {str(e)}")
    
    def create_default_widget(self):
        """创建默认提示页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        hint_label = QLabel("请从左侧选择一个办公工具")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #7f8c8d; font-size: 16px; padding: 50px;")
        
        layout.addWidget(hint_label)
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget