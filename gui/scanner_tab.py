# gui/scanner_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QComboBox, 
    QCheckBox, QProgressBar, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.scanner import DirectoryScanner

class ScannerTab(QWidget):
    result_found = pyqtSignal(dict)  # 扫描结果信号
    
    def __init__(self):
        super().__init__()
        self.scanner = None
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 目标设置组
        target_group = QGroupBox("目标设置")
        target_layout = QHBoxLayout()
        
        self.target_label = QLabel("目标URL:")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("https://example.com")
        
        target_layout.addWidget(self.target_label)
        target_layout.addWidget(self.target_input)
        target_group.setLayout(target_layout)
        
        # 字典设置组
        wordlist_group = QGroupBox("字典设置")
        wordlist_layout = QHBoxLayout()
        
        self.wordlist_label = QLabel("字典文件:")
        self.wordlist_input = QLineEdit()
        self.wordlist_input.setPlaceholderText("选择字典文件...")
        self.wordlist_browse = QPushButton("浏览...")
        self.wordlist_browse.clicked.connect(self.browse_wordlist)
        
        wordlist_layout.addWidget(self.wordlist_label)
        wordlist_layout.addWidget(self.wordlist_input)
        wordlist_layout.addWidget(self.wordlist_browse)
        wordlist_group.setLayout(wordlist_layout)
        
        # 选项设置组
        options_group = QGroupBox("扫描选项")
        options_layout = QVBoxLayout()
        
        # 线程设置
        threads_layout = QHBoxLayout()
        self.threads_label = QLabel("线程数:")
        self.threads_combo = QComboBox()
        self.threads_combo.addItems(["10", "20", "30", "50", "100"])
        self.threads_combo.setCurrentIndex(1)
        threads_layout.addWidget(self.threads_label)
        threads_layout.addWidget(self.threads_combo)
        
        # 扩展名设置
        extensions_layout = QHBoxLayout()
        self.extensions_label = QLabel("扩展名:")
        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText(".bak,.swp,.old")
        extensions_layout.addWidget(self.extensions_label)
        extensions_layout.addWidget(self.extensions_input)
        
        # 复选框选项
        self.ssl_check = QCheckBox("忽略SSL证书错误")
        self.sensitive_check = QCheckBox("检测敏感信息")
        self.verbose_check = QCheckBox("显示详细日志")
        
        options_layout.addLayout(threads_layout)
        options_layout.addLayout(extensions_layout)
        options_layout.addWidget(self.ssl_check)
        options_layout.addWidget(self.sensitive_check)
        options_layout.addWidget(self.verbose_check)
        options_group.setLayout(options_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始扫描")
        self.start_btn.clicked.connect(self.start_scan)
        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("就绪")
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["状态码", "大小", "路径", "敏感信息", "URL"])
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        
        # 日志输出
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # 组装主布局
        main_layout.addWidget(target_group)
        main_layout.addWidget(wordlist_group)
        main_layout.addWidget(options_group)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.result_table, 2)
        main_layout.addWidget(self.log_output, 1)
        
        self.setLayout(main_layout)
    
    def browse_wordlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择字典文件", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            self.wordlist_input.setText(file_path)
    
    def start_scan(self):
        target = self.target_input.text().strip()
        wordlist = self.wordlist_input.text().strip()
        
        if not target:
            self.log("错误：请填写目标URL")
            QMessageBox.warning(self, "输入错误", "请输入目标URL")
            return
            
        if not wordlist:
            self.log("错误：请选择字典文件")
            QMessageBox.warning(self, "输入错误", "请选择字典文件")
            return
        
        # 收集扫描参数
        options = {
            "threads": int(self.threads_combo.currentText()),
            "extensions": self.extensions_input.text().split(',') if self.extensions_input.text() else [],
            "insecure": self.ssl_check.isChecked(),
            "detect_info": self.sensitive_check.isChecked(),
            "verbose": self.verbose_check.isChecked()
        }
        
        # 创建扫描器
        self.scanner = DirectoryScanner(target, wordlist, options)
        self.scanner.progress_signal.connect(self.update_progress)
        self.scanner.result_signal.connect(self.add_result)
        self.scanner.result_signal.connect(self.result_found)  # 连接结果信号
        self.scanner.log_signal.connect(self.log)
        self.scanner.finished_signal.connect(self.scan_finished)
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.result_table.setRowCount(0)
        self.log_output.clear()
        
        # 开始扫描
        self.scanner.start()
    
    def stop_scan(self):
        if self.scanner:
            self.scanner.stop()
            self.log("扫描已停止")
    
    def scan_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setFormat("扫描完成")
        self.log("扫描已完成")
    
    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"扫描中: {current}/{total} ({current/total*100:.1f}%)")
    
    def add_result(self, result):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        self.result_table.setItem(row, 0, QTableWidgetItem(str(result['status'])))
        self.result_table.setItem(row, 1, QTableWidgetItem(str(result['size'])))
        self.result_table.setItem(row, 2, QTableWidgetItem(result['path']))
        
        sensitive = ', '.join(result.get('sensitive_info', []))
        self.result_table.setItem(row, 3, QTableWidgetItem(sensitive))
        
        self.result_table.setItem(row, 4, QTableWidgetItem(result['url']))
    
    def log(self, message):
        self.log_output.append(message)