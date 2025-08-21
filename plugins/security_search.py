import sys
import json
import base64
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QGroupBox, QComboBox, QTextEdit,
    QSplitter, QFileDialog, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from plugins.base_plugin import BasePlugin

class SearchThread(QThread):
    """后台搜索线程"""
    result_received = pyqtSignal(dict, str)  # 搜索结果，来源平台
    error_occurred = pyqtSignal(str)  # 错误信息
    progress_updated = pyqtSignal(int)  # 进度更新

    def __init__(self, platform, api_key, query, size=10):
        super().__init__()
        self.platform = platform
        self.api_key = api_key
        self.query = query
        self.size = size

    def run(self):
        try:
            self.progress_updated.emit(10)
            
            if self.platform == "FOFA":
                result = self.search_fofa()
            elif self.platform == "Hunter":
                result = self.search_hunter()
            elif self.platform == "Quake":
                result = self.search_quake()
            else:
                raise ValueError("未知平台")
            
            self.progress_updated.emit(100)
            self.result_received.emit(result, self.platform)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def search_fofa(self):
        """使用FOFA API进行搜索"""
        url = "https://fofa.info/api/v1/search/all"
        
        # 检查API密钥格式
        if '&' in self.api_key:
            email, key = self.api_key.split('&', 1)
        else:
            email, key = "", self.api_key
            
        params = {
            "email": email,
            "key": key,
            "qbase64": base64.b64encode(self.query.encode('utf-8')).decode('utf-8'),
            "size": self.size,
            "fields": "ip,port,host,domain,server,title,country,city"
        }
        
        self.progress_updated.emit(30)
        response = requests.get(url, params=params, timeout=30)
        self.progress_updated.emit(60)
        
        if response.status_code != 200:
            raise Exception(f"FOFA API错误: {response.status_code} - {response.text}")
        
        data = response.json()
        if data.get("error"):
            raise Exception(f"FOFA错误: {data.get('errmsg')}")
        
        return data

    def search_hunter(self):
        """使用Hunter API进行搜索"""
        url = "https://hunter.qianxin.com/openApi/search"
        params = {
            "api-key": self.api_key,
            "search": base64.b64encode(self.query.encode('utf-8')).decode('utf-8'),
            "page": 1,
            "page_size": self.size,
            "is_web": 1
        }
        
        self.progress_updated.emit(30)
        response = requests.get(url, params=params, timeout=30)
        self.progress_updated.emit(60)
        
        if response.status_code != 200:
            raise Exception(f"Hunter API错误: {response.status_code} - {response.text}")
        
        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"Hunter错误: {data.get('message')}")
        
        return data

    def search_quake(self):
        """使用Quake API进行搜索"""
        url = "https://quake.360.cn/api/v3/search/quake_service"
        headers = {
            "X-QuakeToken": self.api_key
        }
        payload = {
            "query": self.query,
            "start": 0,
            "size": self.size,
            "ignore_cache": False
        }
        
        self.progress_updated.emit(30)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        self.progress_updated.emit(60)
        
        if response.status_code != 200:
            raise Exception(f"Quake API错误: {response.status_code} - {response.text}")
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Quake错误: {data.get('message')}")
        
        return data


class SecuritySearchWidget(QWidget):
    """网络安全信息聚合查询工具界面"""
    def __init__(self):
        super().__init__()
        self.search_thread = None
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("网络安全信息聚合查询工具")
        title_font = QFont("Arial", 12, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 5px;")
        main_layout.addWidget(title_label)
        
        # 配置区域
        config_group = QGroupBox("API配置")
        config_layout = QVBoxLayout()
        
        # 平台选择
        platform_layout = QHBoxLayout()
        self.platform_label = QLabel("选择平台:")
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["FOFA", "Hunter", "Quake"])
        self.platform_combo.currentIndexChanged.connect(self.platform_changed)
        
        platform_layout.addWidget(self.platform_label)
        platform_layout.addWidget(self.platform_combo)
        config_layout.addLayout(platform_layout)
        
        # API密钥输入
        api_layout = QHBoxLayout()
        self.api_label = QLabel("API密钥:")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("在此输入API密钥")
        self.api_input.setEchoMode(QLineEdit.Password)
        
        api_layout.addWidget(self.api_label)
        api_layout.addWidget(self.api_input)
        config_layout.addLayout(api_layout)
        
        # 查询输入
        query_layout = QHBoxLayout()
        self.query_label = QLabel("查询语句:")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("例如: domain=\"example.com\"")
        
        query_layout.addWidget(self.query_label)
        query_layout.addWidget(self.query_input)
        config_layout.addLayout(query_layout)
        
        # 结果数量
        size_layout = QHBoxLayout()
        self.size_label = QLabel("结果数量:")
        self.size_combo = QComboBox()
        self.size_combo.addItems(["10", "20", "50", "100"])
        self.size_combo.setCurrentIndex(0)
        
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_combo)
        config_layout.addLayout(size_layout)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("开始搜索")
        self.search_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; border: none; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2980b9; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.search_btn.clicked.connect(self.start_search)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #9b59b6; color: white; border: none; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #8e44ad; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.search_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 结果展示区域
        result_splitter = QSplitter(Qt.Vertical)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "IP地址", "端口", "主机名", "域名", "服务器", "标题", "国家", "城市"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.result_table.setSortingEnabled(True)
        
        # 原始JSON显示
        self.raw_json_edit = QTextEdit()
        self.raw_json_edit.setReadOnly(True)
        self.raw_json_edit.setPlaceholderText("原始JSON数据将显示在这里...")
        
        # 添加标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.result_table, "表格视图")
        self.tab_widget.addTab(self.raw_json_edit, "原始JSON")
        
        result_splitter.addWidget(self.tab_widget)
        main_layout.addWidget(result_splitter, 1)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 5px; border-top: 1px solid #ecf0f1;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # 初始化平台提示
        self.platform_changed(0)
    
    def platform_changed(self, index):
        """平台选择改变事件"""
        platform = self.platform_combo.currentText()
        if platform == "FOFA":
            self.query_input.setPlaceholderText('例如: domain="example.com"')
            self.status_label.setText("提示: FOFA支持email&key格式或32位/64位key")
        elif platform == "Hunter":
            self.query_input.setPlaceholderText('例如: domain.suffix="example.com"')
            self.status_label.setText("提示: Hunter API密钥为36位字符串")
        elif platform == "Quake":
            self.query_input.setPlaceholderText('例如: domain:"example.com"')
            self.status_label.setText("提示: Quake API密钥为40位字符串")
    
    def start_search(self):
        """开始搜索"""
        platform = self.platform_combo.currentText()
        api_key = self.api_input.text()
        query = self.query_input.text()
        size = int(self.size_combo.currentText())
        
        if not api_key:
            QMessageBox.warning(self, "输入错误", "请输入API密钥")
            return
            
        if not query:
            QMessageBox.warning(self, "输入错误", "请输入查询语句")
            return
            
        # 验证API密钥格式
        if platform == "FOFA" and "&" not in api_key and len(api_key) not in [32, 64]:
            QMessageBox.warning(self, "格式错误", "FOFA API密钥格式应为email&key或32位/64位key")
            return
            
        if platform == "Hunter" and len(api_key) != 36:
            QMessageBox.warning(self, "格式错误", "Hunter API密钥应为36位字符串")
            return
            
        if platform == "Quake" and len(api_key) != 40:
            QMessageBox.warning(self, "格式错误", "Quake API密钥应为40位字符串")
            return
        
        # 禁用按钮
        self.search_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"正在从{platform}搜索...")
        
        # 清空之前的结果
        self.result_table.setRowCount(0)
        self.raw_json_edit.clear()
        
        # 启动搜索线程
        self.search_thread = SearchThread(platform, api_key, query, size)
        self.search_thread.result_received.connect(self.handle_result)
        self.search_thread.error_occurred.connect(self.handle_error)
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.finished.connect(self.search_finished)
        self.search_thread.start()
    
    def search_finished(self):
        """搜索完成回调"""
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def handle_result(self, result, platform):
        """处理搜索结果"""
        try:
            # 显示原始JSON
            self.raw_json_edit.setText(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 解析结果并显示在表格中
            self.parse_and_display_result(result, platform)
            
            self.status_label.setText(f"从{platform}获取到{self.result_table.rowCount()}条结果")
            self.export_btn.setEnabled(True)
        except Exception as e:
            self.handle_error(f"处理结果错误: {str(e)}")
    
    def parse_and_display_result(self, result, platform):
        """解析并显示搜索结果"""
        self.result_table.setRowCount(0)
        
        if platform == "FOFA":
            items = result.get("results", [])
            self.result_table.setRowCount(len(items))
            
            for i, item in enumerate(items):
                for j, value in enumerate(item):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.result_table.setItem(i, j, table_item)
        
        elif platform == "Hunter":
            data = result.get("data", {})
            items = data.get("arr", [])
            self.result_table.setRowCount(len(items))
            
            for i, item in enumerate(items):
                fields = [
                    item.get("ip", ""),
                    item.get("port", ""),
                    item.get("web_title", ""),
                    item.get("domain", ""),
                    item.get("component", [{}])[0].get("name", "") if item.get("component") else "",
                    item.get("title", ""),
                    item.get("country", ""),
                    item.get("city", "")
                ]
                
                for j, value in enumerate(fields):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.result_table.setItem(i, j, table_item)
        
        elif platform == "Quake":
            data = result.get("data", [])
            self.result_table.setRowCount(len(data))
            
            for i, item in enumerate(data):
                service = item.get("service", {})
                location = item.get("location", {})
                
                fields = [
                    item.get("ip", ""),
                    str(service.get("port", "")),
                    service.get("http", {}).get("host", ""),
                    service.get("http", {}).get("host", ""),
                    service.get("http", {}).get("server", ""),
                    service.get("http", {}).get("title", ""),
                    location.get("country_name", ""),
                    location.get("city", "")
                ]
                
                for j, value in enumerate(fields):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    
                    # 高亮重要信息
                    if j == 0 and value:  # IP地址
                        table_item.setBackground(QBrush(QColor("#e3f2fd")))
                    elif j == 4 and "Apache" in value:  # Apache服务器
                        table_item.setBackground(QBrush(QColor("#ffebee")))
                    elif j == 4 and "nginx" in value:  # nginx服务器
                        table_item.setBackground(QBrush(QColor("#e8f5e9")))
                    
                    self.result_table.setItem(i, j, table_item)
    
    def handle_error(self, error_msg):
        """处理错误信息"""
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "搜索错误", error_msg)
    
    def export_results(self):
        """导出搜索结果"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "导出错误", "没有可导出的数据")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "JSON文件 (*.json);;CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith(".json"):
                self.export_to_json(file_path)
            elif file_path.endswith(".csv"):
                self.export_to_csv(file_path)
            elif file_path.endswith(".txt"):
                self.export_to_txt(file_path)
            else:
                file_path += ".json"
                self.export_to_json(file_path)
                
            self.status_label.setText(f"结果已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
    
    def export_to_csv(self, file_path):
        """导出为CSV格式"""
        import csv
        
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # 写入表头
            headers = []
            for col in range(self.result_table.columnCount()):
                headers.append(self.result_table.horizontalHeaderItem(col).text())
            writer.writerow(headers)
            
            # 写入数据
            for row in range(self.result_table.rowCount()):
                row_data = []
                for col in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, col)
                    row_data.append(item.text() if item else "")
                writer.writerow(row_data)
    
    def export_to_txt(self, file_path):
        """导出为文本格式"""
        with open(file_path, "w", encoding="utf-8") as f:
            # 写入表头
            headers = []
            for col in range(self.result_table.columnCount()):
                headers.append(self.result_table.horizontalHeaderItem(col).text())
            f.write("\t".join(headers) + "\n")
            
            # 写入数据
            for row in range(self.result_table.rowCount()):
                row_data = []
                for col in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, col)
                    row_data.append(item.text() if item else "")
                f.write("\t".join(row_data) + "\n")
    
    def export_to_json(self, file_path):
        """导出为JSON格式"""
        results = []
        
        for row in range(self.result_table.rowCount()):
            row_data = {}
            for col in range(self.result_table.columnCount()):
                header = self.result_table.horizontalHeaderItem(col).text()
                item = self.result_table.item(row, col)
                row_data[header] = item.text() if item else ""
            results.append(row_data)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


class SecuritySearchPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "网络资产搜索"
        self.description = "通过FOFA、Hunter、Quake API搜索网络资产信息"
        self.icon = None  # 可以添加图标路径
        self.category = "渗透工具"  # 添加分类属性

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        return SecuritySearchWidget()