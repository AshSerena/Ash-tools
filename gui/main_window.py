import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QAction, 
    QFileDialog, QMessageBox, QMenu, QVBoxLayout,
    QWidget, QSplitter, QToolBar, QLabel
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from gui.scanner_tab import ScannerTab
from gui.result_view import ResultView
from core.plugin_manager import PluginManager
from gui.office_tools_tab import OfficeToolsTab  # 新增办公工具标签页
from gui.plugin_tab import PluginTab  # 添加缺失的导入

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ash - 渗透测试工具包")
        self.setGeometry(100, 100, 1400, 900)  # 增加窗口默认大小
        
        # 初始化插件管理器
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        # self.create_tool_bar()
        
        # 创建主布局
        self.create_main_layout()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 应用现代化主题
        self.apply_modern_theme()
    
    def get_menu_style(self):
        """返回菜单样式表"""
        return """
            QMenu {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2c3e50;
                margin: 4px 0;
            }
        """

    def create_menu_bar(self):
        # 创建菜单栏
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2c3e50;
                color: #ecf0f1;
                padding: 4px 0;
            }
            QMenuBar::item {
                background: transparent;
                color: #ecf0f1;
                padding: 6px 12px;
                margin: 0 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #3498db;
            }
            QMenuBar::item:pressed {
                background-color: #2980b9;
            }
        """)
        
        # 创建文件菜单
        file_menu = menu_bar.addMenu("文件")
        # 直接设置菜单样式，而不是调用不存在的方法
        file_menu.setStyleSheet("""
            QMenu {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2c3e50;
                margin: 4px 0;
            }
        """)
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 创建渗透工具菜单
        self.penetration_menu = menu_bar.addMenu("渗透工具")
        # 直接设置菜单样式
        self.penetration_menu.setStyleSheet("""
            QMenu {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2c3e50;
                margin: 4px 0;
            }
        """)

        # 创建办公工具菜单
        self.office_menu = menu_bar.addMenu("办公工具")
        # 直接设置菜单样式
        self.office_menu.setStyleSheet("""
            QMenu {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2c3e50;
                margin: 4px 0;
            }
        """)
        
        # 创建视图菜单
        view_menu = menu_bar.addMenu("视图")
        view_menu.setStyleSheet(self.get_menu_style())
        
        # 添加显示渗透工具动作
        show_penetration_action = QAction("显示渗透工具", self)
        show_penetration_action.triggered.connect(self.show_penetration_tab)
        view_menu.addAction(show_penetration_action)
        
        # 添加显示办公工具动作
        show_office_action = QAction("显示办公工具", self)
        show_office_action.triggered.connect(self.show_office_tab)
        view_menu.addAction(show_office_action)
        
        # 创建帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        help_menu.setStyleSheet(self.get_menu_style())
        
        # 添加关于动作
        about_action = QAction("关于 Ash", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # 根据插件分类添加到对应菜单
        self.add_plugins_to_menus()

    def show_penetration_tab(self):
        """显示渗透工具标签页"""
        self.tab_widget.setCurrentIndex(0)  # 假设渗透工具是第一个标签页

    def show_office_tab(self):
        """显示办公工具标签页"""
        self.tab_widget.setCurrentIndex(1)  # 假设办公工具是第二个标签页

    def add_plugins_to_menus(self):
        # 清空现有菜单
        self.penetration_menu.clear()
        self.office_menu.clear()
        
        # 为每个插件创建动作并添加到对应菜单
        for plugin in self.plugin_manager.plugins:
            # 创建动作并连接到显示插件的方法
            action = QAction(plugin.name, self)
            action.triggered.connect(lambda checked, p=plugin: self.show_plugin(p))
            
            # 根据插件分类添加到对应菜单
            if plugin.category == "渗透工具":
                self.penetration_menu.addAction(action)
            elif plugin.category == "办公工具":
                self.office_menu.addAction(action)
            else:
                # 对于未分类的插件，默认添加到渗透工具菜单
                self.penetration_menu.addAction(action)

    def show_plugin(self, plugin):
        """显示插件界面"""
        widget = plugin.get_widget()
        if widget:
            # 检查是否已存在该插件的标签页
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == plugin.name:
                    self.tab_widget.setCurrentIndex(i)
                    return
            
            # 添加新标签页
            self.tab_widget.addTab(widget, plugin.name)
            self.tab_widget.setCurrentWidget(widget)
        else:
            QMessageBox.warning(self, "警告", f"插件 {plugin.name} 尚未实现界面组件")
    
    def create_tool_bar(self):
        # 创建主工具栏
        self.main_tool_bar = QToolBar("主工具栏")
        self.main_tool_bar.setIconSize(QSize(24, 24))
        self.main_tool_bar.setMovable(False)
        self.main_tool_bar.setStyleSheet("""
            QToolBar {
                background-color: #34495e;
                border: none;
                padding: 4px;
                spacing: 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #ecf0f1;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #4a6a8d;
                border: 1px solid #1abc9c;
            }
            QToolButton:checked, QToolButton:pressed {
                background-color: #1abc9c;
                color: #ffffff;
            }
        """)
        self.addToolBar(Qt.TopToolBarArea, self.main_tool_bar)
        
        
        # 创建渗透工具工具栏
        self.penetration_tool_bar = QToolBar("渗透工具")
        self.penetration_tool_bar.setObjectName("PenetrationToolBar")
        self.penetration_tool_bar.setIconSize(QSize(20, 20))
        self.penetration_tool_bar.setStyleSheet(self.main_tool_bar.styleSheet())
        self.addToolBar(Qt.TopToolBarArea, self.penetration_tool_bar)
        
        # 创建办公工具工具栏
        self.office_tool_bar = QToolBar("办公工具")
        self.office_tool_bar.setObjectName("OfficeToolBar")
        self.office_tool_bar.setIconSize(QSize(20, 20))
        self.office_tool_bar.setStyleSheet(self.main_tool_bar.styleSheet())
        self.addToolBar(Qt.TopToolBarArea, self.office_tool_bar)
        
        # 根据插件分类添加工具栏按钮
        self.add_plugins_to_toolbars()
    
    def add_plugins_to_toolbars(self):
        # 清空现有工具栏
        self.penetration_tool_bar.clear()
        self.office_tool_bar.clear()
        
        # 为每个插件创建工具栏按钮
        for plugin in self.plugin_manager.plugins:
            # 创建动作并连接到显示插件的方法
            action = QAction(plugin.name, self)
            action.triggered.connect(lambda checked, p=plugin: self.show_plugin(p))
            action.setIconText(plugin.name)  # 设置按钮文本
            
            # 根据插件分类添加到对应工具栏
            if plugin.category == "渗透工具":
                self.penetration_tool_bar.addAction(action)
            elif plugin.category == "办公工具":
                self.office_tool_bar.addAction(action)
            else:
                # 对于未分类的插件，默认添加到渗透工具工具栏
                self.penetration_tool_bar.addAction(action)
    
    def create_main_layout(self):
        # 创建中心部件和布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 初始化标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2c3e50;
                background: #ecf0f1;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #95a5a6;
                color: #2c3e50;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #bdc3c7;
            }
            QTabBar::close-button {
                image: none;
                subcontrol-origin: padding;
                subcontrol-position: right;
                padding: 4px;
            }
            QTabBar::close-button:hover {
                background: #e74c3c;
                border-radius: 4px;
            }
        """)
        
        # 创建渗透工具标签页
        self.penetration_tab = PluginTab(self.plugin_manager)
        self.tab_widget.addTab(self.penetration_tab, "渗透工具")
        
        # 创建办公工具标签页
        self.office_tab = OfficeToolsTab(self.plugin_manager)
        self.tab_widget.addTab(self.office_tab, "办公工具")
        
        # 添加标签页控件到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 设置中心部件
        self.setCentralWidget(central_widget)
    
    def create_status_bar(self):
        # 创建状态栏
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #34495e;
                color: #ecf0f1;
                border-top: 1px solid #2c3e50;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # 添加状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #ecf0f1; padding: 4px;")
        status_bar.addWidget(self.status_label, 1)
        
        # 添加版本信息
        version_label = QLabel("Ash v1.0.0")
        version_label.setStyleSheet("color: #ecf0f1; padding: 4px;")
        status_bar.addPermanentWidget(version_label)
        
        self.setStatusBar(status_bar)
    
    def show_about(self):
        about_text = """
        <h3>Ash - 渗透测试工具包</h3>
        <p>版本: 1.0.0</p>
        <p>开发者: Ash</p>
        <p>一款集成了多种渗透测试和办公工具的综合性平台，</p>
        <p>旨在提高安全测试人员的工作效率。</p>
        """
        msg = QMessageBox(self)
        msg.setIconPixmap(self.style().standardIcon(self.style().SP_MessageBoxInformation).pixmap(64, 64))
        msg.setWindowTitle("关于 Ash")
        msg.setText(about_text)
        msg.setStyleSheet("QLabel{min-width: 300px;}")
        msg.exec_()

    def close_tab(self, index):
        """关闭标签页"""
        if index > 1:  # 不关闭前两个固定标签页
            widget = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            widget.deleteLater()

    def apply_modern_theme(self):
        """应用现代化主题"""
        # 设置应用程序字体
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        
        # 设置调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(236, 240, 241))
        palette.setColor(QPalette.WindowText, QColor(44, 62, 80))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(236, 240, 241))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(44, 62, 80))
        palette.setColor(QPalette.Text, QColor(44, 62, 80))
        palette.setColor(QPalette.Button, QColor(52, 73, 94))
        palette.setColor(QPalette.ButtonText, QColor(236, 240, 241))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(52, 152, 219))
        palette.setColor(QPalette.Highlight, QColor(26, 188, 156))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        # 设置应用程序样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QWidget {
                selection-background-color: #1abc9c;
                selection-color: white;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 6px;
                background: white;
                selection-background-color: #1abc9c;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #3498db;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }
        """)