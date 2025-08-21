import os
import re
import json
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QSplitter, QProgressBar, QMessageBox, QGroupBox, 
    QCheckBox, QMenu, QApplication, QHeaderView, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QBrush, QColor
from plugins.base_plugin import BasePlugin

class SensitiveInfoScannerThread(QThread):
    progress = pyqtSignal(int, str)
    scan_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, scan_dir, file_extensions, max_file_size, exclude_dirs=None):
        super().__init__()
        self.scan_dir = scan_dir
        self.file_extensions = file_extensions
        self.max_file_size = max_file_size * 1024 * 1024  # 转换为字节
        self.exclude_dirs = exclude_dirs or ['.git', 'node_modules', 'vendor', '__pycache__']
        self.results = []
        self.running = True
        self.patterns = self.get_sensitive_patterns()

    def get_sensitive_patterns(self):
        """定义敏感信息模式的正则表达式"""
        return [
            # API密钥和令牌 - 增加上下文要求
            {"name": "API Key", "pattern": r'(?i)(?:api[_-]?key|access[_-]?key|secret[_-]?key)[\s=:]+["\']([0-9a-zA-Z\-_]{10,50})["\']', "severity": "high"},
            {"name": "App Secret", "pattern": r'(?i)(?:app[_-]?secret|client[_-]?secret)[\s=:]+["\']([0-9a-zA-Z\-_]{10,50})["\']', "severity": "critical"},
            {"name": "Bearer Token", "pattern": r'(?i)bearer[\s]+([a-zA-Z0-9\-_]{20,100})', "severity": "critical"},
            {"name": "JWT Token", "pattern": r'\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b', "severity": "high"},
            
            # 密码 - 增加上下文要求
            {"name": "Password", "pattern": r'(?i)(?:password|passwd|pwd)[\s=:]+["\']([^"\'\s]{8,50})["\']', "severity": "critical"},
            {"name": "Password in Config", "pattern": r'(?i)<password>([^<]{8,50})</password>', "severity": "critical"},
            
            # 认证信息 - 增加上下文要求
            {"name": "Basic Auth", "pattern": r'(?i)authorization:\s*basic\s+([a-zA-Z0-9=+/]{20,})', "severity": "high"},
            
            # 数据库连接字符串 - 增加上下文要求
            {"name": "Database Connection", "pattern": r'(?i)(?:postgresql|mysql|mongodb|sqlserver)://[a-zA-Z0-9_]+:([^@\s]{8,50})@[a-zA-Z0-9.\-_]+', "severity": "critical"},
            
            # 云服务凭证 - 增加前缀和上下文要求
            {"name": "AWS Access Key", "pattern": r'(?i)(?:aws[_-]?access[_-]?key|aws[_-]?key)[\s=:]+["\']?(AKIA[0-9A-Z]{16})["\']?', "severity": "critical"},
            {"name": "AWS Secret Key", "pattern": r'(?i)(?:aws[_-]?secret[_-]?access[_-]?key|aws[_-]?secret[_-]?key)[\s=:]+["\']([0-9a-zA-Z/+]{40})["\']', "severity": "critical"},
            {"name": "Google API Key", "pattern": r'(?i)(?:google[_-]?api[_-]?key|gcp[_-]?key)[\s=:]+["\']?(AIza[0-9A-Za-z\-_]{35})["\']?', "severity": "high"},
            {"name": "Google Cloud Key", "pattern": r'(?i)(?:google[_-]?cloud[_-]?key|gcp[_-]?service[_-]?key)[\s=:]+["\']?(GOOG[0-9A-Za-z\-_]{10,30})["\']?', "severity": "high"},
            {"name": "Azure Key", "pattern": r'(?i)(?:azure[_-]?key|microsoft[_-]?azure[_-]?key)[\s=:]+["\']?(AZ[0-9A-Za-z\-_]{34,40})["\']?', "severity": "high"},
            {"name": "IBM Cloud Key", "pattern": r'(?i)(?:ibm[_-]?cloud[_-]?key|bluemix[_-]?key)[\s=:]+["\']?(IBM[0-9A-Za-z\-_]{10,40})["\']?', "severity": "high"},
            {"name": "Oracle Cloud Key", "pattern": r'(?i)(?:oracle[_-]?cloud[_-]?key|oci[_-]?key)[\s=:]+["\']?(OCID[0-9A-Za-z\-_]{10,40})["\']?', "severity": "high"},
            {"name": "Alibaba Cloud Key", "pattern": r'(?i)(?:alibaba[_-]?cloud[_-]?key|aliyun[_-]?key)[\s=:]+["\']?(LTAI[0-9A-Za-z\-_]{12,20})["\']?', "severity": "high"},
            {"name": "Tencent Cloud Key", "pattern": r'(?i)(?:tencent[_-]?cloud[_-]?key|qcloud[_-]?key)[\s=:]+["\']?(AKID[0-9A-Za-z\-_]{13,20})["\']?', "severity": "high"},
            {"name": "Huawei Cloud Key", "pattern": r'(?i)(?:huawei[_-]?cloud[_-]?key|hwcloud[_-]?key)[\s=:]+["\']?(AK[0-9A-Za-z\-_]{10,62})["\']?', "severity": "high"},
            {"name": "Baidu Cloud Key", "pattern": r'(?i)(?:baidu[_-]?cloud[_-]?key|bce[_-]?key)[\s=:]+["\']?(AK[0-9A-Za-z\-_]{10,40})["\']?', "severity": "high"},
            {"name": "JD Cloud Key", "pattern": r'(?i)(?:jd[_-]?cloud[_-]?key|jdcloud[_-]?key)[\s=:]+["\']?(JDC_[A-Z0-9]{28,32})["\']?', "severity": "high"},
            {"name": "Volcano Engine Key", "pattern": r'(?i)(?:volcano[_-]?engine[_-]?key|byteplus[_-]?key)[\s=:]+["\']?(AKLT[0-9A-Za-z\-_]{0,252})["\']?', "severity": "high"},
            {"name": "UCloud Key", "pattern": r'(?i)(?:ucloud[_-]?key)[\s=:]+["\']?(UC[0-9A-Za-z\-_]{10,40})["\']?', "severity": "high"},
            {"name": "China Unicom Cloud Key", "pattern": r'(?i)(?:unicom[_-]?cloud[_-]?key|cucloud[_-]?key)[\s=:]+["\']?(LTC[0-9A-Za-z\-_]{10,60})["\']?', "severity": "high"},
            {"name": "China Mobile Cloud Key", "pattern": r'(?i)(?:mobile[_-]?cloud[_-]?key|cmcloud[_-]?key)[\s=:]+["\']?(YD[0-9A-Za-z\-_]{10,60})["\']?', "severity": "high"},
            {"name": "China Telecom Cloud Key", "pattern": r'(?i)(?:telecom[_-]?cloud[_-]?key|ctcloud[_-]?key)[\s=:]+["\']?(CTC[0-9A-Za-z\-_]{10,60})["\']?', "severity": "high"},
            {"name": "Yonyou Cloud Key", "pattern": r'(?i)(?:yonyou[_-]?cloud[_-]?key|yycloud[_-]?key)[\s=:]+["\']?(YY[0-9A-Za-z\-_]{10,40})["\']?', "severity": "high"},
            
            # 个人身份信息 - 增加边界检查
            {"name": "Email Address", "pattern": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', "severity": "medium"},
            {"name": "Credit Card", "pattern": r'\b(?:\d[ -]*?){13,16}\b', "severity": "high"},
            {"name": "SSN", "pattern": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b', "severity": "high"},
            {"name": "Phone Number", "pattern": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', "severity": "medium"},
            
            # 其他敏感信息 - 增加上下文要求
            {"name": "Private Key", "pattern": r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', "severity": "critical"},
            {"name": "License Key", "pattern": r'(?i)(?:license|licence|serial)[_-]?key[\s=:]+["\']?([0-9a-zA-Z\-_]{10,30})["\']?', "severity": "medium"},
            {"name": "Sensitive URL", "pattern": r'(?i)(?:admin|login|private|secret)[^\s/]*\.(?:php|asp|aspx|jsp|html)', "severity": "medium"},
            
            # 通用密钥模式 - 增加上下文要求
            {"name": "Generic Key Pattern", "pattern": r'(?i)(?:access[_-]?key|secret[_-]?key|api[_-]?key|client[_-]?secret|app[_-]?secret)[\s=:]+["\']?([0-9a-zA-Z\-_+=/]{10,100})["\']?', "severity": "high"},
            
            # 配置文件中的敏感信息 - 增加上下文要求
            {"name": "Config Secret", "pattern": r'(?i)(?:password|passwd|pwd|secret|key|token)[\s=:]+["\']?([^"\'\s]{8,50})["\']?', "severity": "medium"},
        ]

    def run(self):
        try:
            if not os.path.exists(self.scan_dir):
                raise FileNotFoundError(f"目录不存在: {self.scan_dir}")
            
            self.progress.emit(0, "正在扫描文件...")
            
            # 收集所有要扫描的文件
            file_paths = []
            for root, dirs, files in os.walk(self.scan_dir):
                if not self.running:
                    self.progress.emit(0, "扫描已中止")
                    return
                
                # 排除不需要的目录
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 检查文件扩展名
                    if self.file_extensions:
                        ext = os.path.splitext(file)[1].lower()
                        if ext not in self.file_extensions:
                            continue
                    
                    # 检查文件大小
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > self.max_file_size:
                            self.progress.emit(0, f"跳过大文件: {file} ({file_size//1024}KB)")
                            continue
                    except Exception:
                        continue
                    
                    file_paths.append(file_path)
            
            total_files = len(file_paths)
            if total_files == 0:
                self.progress.emit(100, "没有找到可扫描的文件")
                self.scan_finished.emit([])
                return
            
            # 扫描文件
            results = []
            for idx, file_path in enumerate(file_paths):
                if not self.running:
                    self.progress.emit(0, "扫描已中止")
                    return
                
                try:
                    # 更新进度
                    progress = int((idx + 1) / total_files * 100)
                    self.progress.emit(progress, f"扫描中: {os.path.basename(file_path)}")
                    
                    # 扫描文件
                    file_results = self.scan_file(file_path)
                    if file_results:
                        results.extend(file_results)
                except Exception as e:
                    self.progress.emit(progress, f"扫描文件出错: {file_path} - {str(e)}")
            
            self.scan_finished.emit(results)
            self.progress.emit(100, f"扫描完成! 发现 {len(results)} 条敏感信息")
            
        except Exception as e:
            error_msg = f"扫描出错: {str(e)}"
            self.progress.emit(0, error_msg)
            self.error_occurred.emit(error_msg)

    def scan_file(self, file_path):
        """扫描单个文件中的敏感信息"""
        results = []
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 应用所有正则模式
            for pattern in self.patterns:
                matches = re.finditer(pattern["pattern"], content)
                for match in matches:
                    # 获取匹配的上下文
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end].replace('\n', ' ').replace('\r', ' ')
                    
                    result = {
                        "file": file_path,
                        "type": pattern["name"],
                        "severity": pattern["severity"],
                        "match": match.group(0),
                        "line": self.get_line_number(content, match.start()),
                        "context": context
                    }
                    results.append(result)
                    
                    if not self.running:
                        return results
            
        except Exception as e:
            self.progress.emit(0, f"扫描文件出错: {file_path} - {str(e)}")
        
        return results

    def get_line_number(self, content, position):
        """获取匹配位置的行号"""
        line_count = 1
        current_pos = 0
        
        for char in content:
            if current_pos >= position:
                return line_count
            if char == '\n':
                line_count += 1
            current_pos += 1
        
        return line_count

    def stop(self):
        self.running = False

class SensitiveInfoScannerPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "敏感信息扫描"
        self.description = "扫描代码中的敏感信息"
        self.category = "渗透工具"
    
    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        default_extensions = ['.py', '.js', '.php', '.html', '.css', '.ini', '.conf', '.env', '.txt', '.json', '.xml', '.yml', '.yaml']
        return SensitiveInfoScannerWidget(default_extensions)

class SensitiveInfoScannerWidget(QWidget):
    def __init__(self, default_extensions):
        super().__init__()
        self.scan_dir = os.getcwd()
        self.default_extensions = default_extensions
        self.scanner = None
        self.results = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 目录选择区域
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("扫描目录:")
        self.dir_input = QLineEdit(self.scan_dir)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        
        # 配置选项区域
        config_group = QGroupBox("扫描配置")
        config_layout = QVBoxLayout()
        
        # 文件扩展名过滤
        ext_layout = QHBoxLayout()
        self.ext_label = QLabel("文件扩展名:")
        self.ext_input = QLineEdit(", ".join(self.default_extensions))
        self.ext_input.setToolTip("逗号分隔的文件扩展名列表（例如：.js, .py, .json）")
        ext_layout.addWidget(self.ext_label)
        ext_layout.addWidget(self.ext_input)
        
        # 文件大小限制
        size_layout = QHBoxLayout()
        self.size_label = QLabel("最大文件大小(MB):")
        self.size_input = QLineEdit("10")
        self.size_input.setToolTip("大于此大小的文件将被跳过")
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_input)
        
        # 排除目录
        exclude_layout = QHBoxLayout()
        self.exclude_label = QLabel("排除目录:")
        self.exclude_input = QLineEdit(".git, node_modules, vendor, __pycache__")
        self.exclude_input.setToolTip("逗号分隔的目录名列表，这些目录将被跳过")
        exclude_layout.addWidget(self.exclude_label)
        exclude_layout.addWidget(self.exclude_input)
        
        config_layout.addLayout(ext_layout)
        config_layout.addLayout(size_layout)
        config_layout.addLayout(exclude_layout)
        config_group.setLayout(config_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.clicked.connect(self.start_scan)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)
        self.export_btn = QPushButton("导出结果")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_results)
        
        control_layout.addWidget(self.scan_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.export_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("就绪")
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 结果展示区域
        self.result_tabs = QTabWidget()
        
        # 表格视图
        self.result_table = QTreeWidget()
        self.result_table.setHeaderLabels(["文件", "类型", "严重性", "匹配内容", "行号"])
        self.result_table.setColumnWidth(0, 300)
        self.result_table.setColumnWidth(1, 150)
        self.result_table.setColumnWidth(2, 80)
        self.result_table.setColumnWidth(3, 300)
        self.result_table.setColumnWidth(4, 60)
        self.result_table.header().setSectionResizeMode(QHeaderView.Interactive)
        self.result_table.itemDoubleClicked.connect(self.show_detail)
        
        # 详情视图
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setPlaceholderText("双击表格中的项目查看详情...")
        
        # 添加标签页
        self.result_tabs.addTab(self.result_table, "扫描结果")
        self.result_tabs.addTab(self.detail_view, "详情")
        
        # 组装界面
        main_layout.addLayout(dir_layout)
        main_layout.addWidget(config_group)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.result_tabs, 1)
        
        self.setLayout(main_layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择扫描目录", self.scan_dir
        )
        if dir_path:
            self.scan_dir = dir_path
            self.dir_input.setText(dir_path)
    
    def start_scan(self):
        scan_dir = self.dir_input.text().strip()
        if not scan_dir:
            QMessageBox.warning(self, "输入错误", "请选择扫描目录")
            return
        
        # 获取文件扩展名
        ext_text = self.ext_input.text().strip()
        if ext_text:
            file_extensions = [ext.strip().lower() for ext in ext_text.split(',') if ext.strip()]
        else:
            file_extensions = self.default_extensions
        
        # 获取最大文件大小
        try:
            max_file_size = int(self.size_input.text().strip())
        except ValueError:
            max_file_size = 10  # 默认10MB
        
        # 获取排除目录
        exclude_text = self.exclude_input.text().strip()
        exclude_dirs = [d.strip() for d in exclude_text.split(',')] if exclude_text else []
        
        # 重置UI状态
        self.result_table.clear()
        self.detail_view.clear()
        self.export_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在准备扫描...")
        
        # 创建扫描器
        self.scanner = SensitiveInfoScannerThread(scan_dir, file_extensions, max_file_size, exclude_dirs)
        self.scanner.progress.connect(self.update_progress)
        self.scanner.scan_finished.connect(self.scan_finished)
        self.scanner.error_occurred.connect(self.handle_error)
        
        # 更新按钮状态
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 开始扫描
        self.scanner.start()
    
    def stop_scan(self):
        if self.scanner:
            self.scanner.stop()
            self.status_label.setText("扫描已停止")
            self.scan_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def scan_finished(self, results):
        # 更新按钮状态
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(bool(results))
        
        # 保存结果
        self.results = results
        
        # 显示结果
        self.display_results(results)
        
        # 更新状态
        if results:
            self.status_label.setText(f"扫描完成! 发现 {len(results)} 条敏感信息")
        else:
            self.status_label.setText("扫描完成! 未发现敏感信息")
    
    def display_results(self, results):
        """在表格中显示扫描结果"""
        self.result_table.clear()
        
        # 按严重性分组
        groups = {}
        for result in results:
            severity = result["severity"]
            if severity not in groups:
                groups[severity] = []
            groups[severity].append(result)
        
        # 按严重性排序（critical > high > medium > low）
        severity_order = ["critical", "high", "medium", "low"]
        for severity in severity_order:
            if severity in groups:
                group_item = QTreeWidgetItem(self.result_table, [f"{severity.capitalize()} 风险", "", "", "", ""])
                group_item.setExpanded(True)
                
                # 设置颜色
                if severity == "critical":
                    group_item.setBackground(0, QBrush(QColor(255, 200, 200)))
                elif severity == "high":
                    group_item.setBackground(0, QBrush(QColor(255, 225, 200)))
                elif severity == "medium":
                    group_item.setBackground(0, QBrush(QColor(255, 255, 200)))
                
                for result in groups[severity]:
                    file_name = os.path.basename(result["file"])
                    file_path = result["file"]
                    match_preview = result["match"][:50] + ("..." if len(result["match"]) > 50 else "")
                    
                    item = QTreeWidgetItem(group_item, [
                        file_name,
                        result["type"],
                        severity.capitalize(),
                        match_preview,
                        str(result["line"])
                    ])
                    item.setData(0, Qt.UserRole, result)
                    
                    # 设置颜色
                    if severity == "critical":
                        item.setBackground(2, QBrush(QColor(255, 200, 200)))
                    elif severity == "high":
                        item.setBackground(2, QBrush(QColor(255, 225, 200)))
    
    def show_detail(self, item, column):
        """显示选中项的详细信息"""
        result = item.data(0, Qt.UserRole)
        if not result:
            return
        
        detail_text = f"""=== 敏感信息详情 ===
文件: {result['file']}
类型: {result['type']}
严重性: {result['severity'].capitalize()}
行号: {result['line']}

匹配内容:
{result['match']}

上下文:
...{result['context']}...
"""
        self.detail_view.setText(detail_text)
        self.result_tabs.setCurrentIndex(1)  # 切换到详情标签页
    
    def export_results(self):
        """导出扫描结果"""
        if not self.results:
            QMessageBox.information(self, "导出结果", "没有结果可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出扫描结果", "", "JSON 文件 (*.json);;文本文件 (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.json'):
                # 导出为JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
            else:
                # 导出为文本
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=== 敏感信息扫描结果 ===\n")
                    f.write(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"扫描目录: {self.dir_input.text()}\n")
                    f.write(f"发现 {len(self.results)} 条敏感信息\n\n")
                    
                    for result in self.results:
                        f.write(f"文件: {result['file']}\n")
                        f.write(f"类型: {result['type']}\n")
                        f.write(f"严重性: {result['severity']}\n")
                        f.write(f"行号: {result['line']}\n")
                        f.write(f"匹配内容: {result['match']}\n")
                        f.write(f"上下文: ...{result['context']}...\n")
                        f.write("-" * 80 + "\n")
            
            QMessageBox.information(self, "导出成功", f"结果已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出结果失败: {str(e)}")
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def handle_error(self, error_msg):
        self.status_label.setText(error_msg)
        QMessageBox.critical(self, "扫描错误", error_msg)
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)