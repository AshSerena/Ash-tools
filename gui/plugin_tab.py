from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QListWidget, QLabel, QStackedWidget, QListWidgetItem
from PyQt5.QtCore import Qt

class PluginTab(QWidget):
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
        
        # 加载渗透工具插件
        self.load_penetration_plugins()
        
        plugin_list_layout.addWidget(QLabel("选择工具:"))
        plugin_list_layout.addWidget(self.plugin_list)
        
        # 创建插件显示区域
        self.plugin_display = QStackedWidget()
        
        # 添加分割器到主布局
        splitter.addWidget(plugin_list_widget)
        splitter.addWidget(self.plugin_display)
        splitter.setSizes([200, 800])  # 设置分割比例
        
        main_layout.addWidget(splitter)
    
    def load_penetration_plugins(self):
        # 清空插件列表
        self.plugin_list.clear()
        
        # 加载所有渗透工具插件
        for plugin in self.plugin_manager.plugins:
            if plugin.category == "渗透工具":
                item = QListWidgetItem(plugin.name)
                item.setData(Qt.UserRole, plugin)
                self.plugin_list.addItem(item)
    
    def show_plugin(self, item):
        # 获取插件
        plugin = item.data(Qt.UserRole)
        
        # 如果插件已经加载，则切换到该插件
        for i in range(self.plugin_display.count()):
            if self.plugin_display.widget(i).property("plugin_name") == plugin.name:
                self.plugin_display.setCurrentIndex(i)
                self.current_plugin = plugin
                return
        
        # 加载新插件
        widget = plugin.get_widget()
        widget.setProperty("plugin_name", plugin.name)
        self.plugin_display.addWidget(widget)
        self.plugin_display.setCurrentIndex(self.plugin_display.count() - 1)
        self.current_plugin = plugin