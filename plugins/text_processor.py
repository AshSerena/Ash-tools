import os
import re
import difflib
import html
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QComboBox, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog, QSplitter,
    QListWidget, QListWidgetItem, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QToolBar, QAction,
    QFontComboBox, QSpinBox, QColorDialog, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QSyntaxHighlighter, QColor, QTextDocument, QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView
from plugins.base_plugin import BasePlugin

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class TextProcessingThread(QThread):
    """文本处理线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 当前状态
    task_completed = pyqtSignal(str, object)  # 完成消息, 结果数据
    error_occurred = pyqtSignal(str)         # 错误消息

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs
        self.cancel_requested = False

    def run(self):
        try:
            if self.task_type == "compare_texts":
                self.compare_texts()
            elif self.task_type == "extract_text":
                self.extract_text()
            elif self.task_type == "convert_markdown":
                self.convert_markdown()
        except Exception as e:
            self.error_occurred.emit(f"处理错误: {str(e)}")

    def compare_texts(self):
        """比较文本"""
        text1 = self.kwargs.get('text1', '')
        text2 = self.kwargs.get('text2', '')
        ignore_case = self.kwargs.get('ignore_case', False)
        ignore_whitespace = self.kwargs.get('ignore_whitespace', False)
        
        if not text1 or not text2:
            self.error_occurred.emit("请输入要比较的文本")
            return
            
        # 预处理文本
        if ignore_case:
            text1 = text1.lower()
            text2 = text2.lower()
            
        if ignore_whitespace:
            text1 = re.sub(r'\s+', ' ', text1).strip()
            text2 = re.sub(r'\s+', ' ', text2).strip()
        
        # 比较文本
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # 使用difflib生成差异
        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))
        
        # 计算相似度
        matcher = difflib.SequenceMatcher(None, text1, text2)
        similarity = matcher.ratio() * 100
        
        self.progress_updated.emit(100, "比较完成")
        self.task_completed.emit("文本比较完成", {
            'diff': diff,
            'similarity': similarity,
            'lines1': len(lines1),
            'lines2': len(lines2),
            'chars1': len(text1),
            'chars2': len(text2)
        })
    
    def extract_text(self):
        """提取文本"""
        source_text = self.kwargs.get('source_text', '')
        extract_type = self.kwargs.get('extract_type', 'html')
        
        if not source_text:
            self.error_occurred.emit("请输入要提取的文本")
            return
            
        result = ""
        
        if extract_type == 'html':
            if not BEAUTIFULSOUP_AVAILABLE:
                self.error_occurred.emit("需要安装BeautifulSoup库: pip install beautifulsoup4")
                return
                
            try:
                soup = BeautifulSoup(source_text, 'html.parser')
                
                # 移除脚本和样式标签
                for script in soup(["script", "style"]):
                    script.extract()
                
                # 获取文本
                text = soup.get_text()
                
                # 处理空白字符
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                result = '\n'.join(chunk for chunk in chunks if chunk)
                
            except Exception as e:
                self.error_occurred.emit(f"HTML解析错误: {str(e)}")
                return
                
        elif extract_type == 'urls':
            # 提取URL
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', source_text)
            result = '\n'.join(urls)
            
        elif extract_type == 'emails':
            # 提取邮箱
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', source_text)
            result = '\n'.join(emails)
            
        elif extract_type == 'phones':
            # 提取电话号码
            phones = re.findall(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})', source_text)
            result = '\n'.join(phones)
        
        self.progress_updated.emit(100, "提取完成")
        self.task_completed.emit("文本提取完成", {'result': result})
    
    def convert_markdown(self):
        """转换Markdown"""
        markdown_text = self.kwargs.get('markdown_text', '')
        output_format = self.kwargs.get('output_format', 'html')
        
        if not markdown_text:
            self.error_occurred.emit("请输入Markdown文本")
            return
            
        if not MARKDOWN_AVAILABLE:
            self.error_occurred.emit("需要安装Markdown库: pip install markdown")
            return
            
        try:
            if output_format == 'html':
                # 转换为HTML
                html_text = markdown.markdown(markdown_text, extensions=['extra', 'tables', 'codehilite'])
                self.task_completed.emit("Markdown转换完成", {'result': html_text, 'format': 'html'})
                
            elif output_format == 'plain':
                # 转换为纯文本（通过HTML中转）
                html_text = markdown.markdown(markdown_text)
                # 移除HTML标签
                clean_text = re.sub('<[^<]+?>', '', html_text)
                self.task_completed.emit("Markdown转换完成", {'result': clean_text, 'format': 'plain'})
                
        except Exception as e:
            self.error_occurred.emit(f"Markdown转换错误: {str(e)}")
    
    def cancel(self):
        self.cancel_requested = True


class DiffHighlighter(QSyntaxHighlighter):
    """差异高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.add_format = QTextCharFormat()
        self.add_format.setBackground(QColor(200, 255, 200))  # 浅绿色背景
        
        self.remove_format = QTextCharFormat()
        self.remove_format.setBackground(QColor(255, 200, 200))  # 浅红色背景
        self.remove_format.setProperty(QTextCharFormat.TextUnderlineStyle, True)
        
        self.change_format = QTextCharFormat()
        self.change_format.setBackground(QColor(255, 255, 200))  # 浅黄色背景
    
    def highlightBlock(self, text):
        if text.startswith('+ '):
            self.setFormat(0, len(text), self.add_format)
        elif text.startswith('- '):
            self.setFormat(0, len(text), self.remove_format)
        elif text.startswith('? '):
            self.setFormat(0, len(text), self.change_format)


class TextProcessorWidget(QWidget):
    """文本处理工具界面"""
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("文本处理工具")
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 添加各个功能选项卡
        self.tab_widget.addTab(self.create_text_comparison_tab(), "文本比较")
        self.tab_widget.addTab(self.create_text_extraction_tab(), "文本提取")
        self.tab_widget.addTab(self.create_markdown_conversion_tab(), "Markdown转换")
        
        main_layout.addWidget(self.tab_widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 5px; border-top: 1px solid #ecf0f1;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
    
    def create_text_comparison_tab(self):
        """创建文本比较选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout()
        
        # 第一个文件
        file1_layout = QVBoxLayout()
        file1_layout.addWidget(QLabel("文件1:"))
        
        file1_path_layout = QHBoxLayout()
        self.file1_path = QLineEdit()
        self.file1_path.setPlaceholderText("选择第一个文件...")
        self.browse_file1_btn = QPushButton("浏览...")
        self.browse_file1_btn.clicked.connect(lambda: self.browse_file(self.file1_path))
        
        file1_path_layout.addWidget(self.file1_path)
        file1_path_layout.addWidget(self.browse_file1_btn)
        
        self.load_file1_btn = QPushButton("加载文件")
        self.load_file1_btn.clicked.connect(lambda: self.load_file(self.file1_path, self.text1_edit))
        
        file1_layout.addLayout(file1_path_layout)
        file1_layout.addWidget(self.load_file1_btn)
        
        # 第二个文件
        file2_layout = QVBoxLayout()
        file2_layout.addWidget(QLabel("文件2:"))
        
        file2_path_layout = QHBoxLayout()
        self.file2_path = QLineEdit()
        self.file2_path.setPlaceholderText("选择第二个文件...")
        self.browse_file2_btn = QPushButton("浏览...")
        self.browse_file2_btn.clicked.connect(lambda: self.browse_file(self.file2_path))
        
        file2_path_layout.addWidget(self.file2_path)
        file2_path_layout.addWidget(self.browse_file2_btn)
        
        self.load_file2_btn = QPushButton("加载文件")
        self.load_file2_btn.clicked.connect(lambda: self.load_file(self.file2_path, self.text2_edit))
        
        file2_layout.addLayout(file2_path_layout)
        file2_layout.addWidget(self.load_file2_btn)
        
        file_layout.addLayout(file1_layout)
        file_layout.addLayout(file2_layout)
        file_group.setLayout(file_layout)
        
        # 比较选项
        options_group = QGroupBox("比较选项")
        options_layout = QHBoxLayout()
        
        self.ignore_case_check = QCheckBox("忽略大小写")
        self.ignore_case_check.setChecked(True)
        
        self.ignore_whitespace_check = QCheckBox("忽略空白字符")
        self.ignore_whitespace_check.setChecked(False)
        
        options_layout.addWidget(self.ignore_case_check)
        options_layout.addWidget(self.ignore_whitespace_check)
        options_layout.addStretch()
        
        options_group.setLayout(options_layout)
        
        # 文本编辑区域
        text_edit_group = QGroupBox("文本内容")
        text_edit_layout = QHBoxLayout()
        
        # 第一个文本编辑器
        text1_layout = QVBoxLayout()
        text1_layout.addWidget(QLabel("文本1:"))
        self.text1_edit = QTextEdit()
        self.text1_edit.setPlaceholderText("在此输入或粘贴第一个文本...")
        text1_layout.addWidget(self.text1_edit)
        
        # 第二个文本编辑器
        text2_layout = QVBoxLayout()
        text2_layout.addWidget(QLabel("文本2:"))
        self.text2_edit = QTextEdit()
        self.text2_edit.setPlaceholderText("在此输入或粘贴第二个文本...")
        text2_layout.addWidget(self.text2_edit)
        
        text_edit_layout.addLayout(text1_layout)
        text_edit_layout.addLayout(text2_layout)
        text_edit_group.setLayout(text_edit_layout)
        
        # 比较按钮
        self.compare_btn = QPushButton("比较文本")
        self.compare_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2980b9; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.compare_btn.clicked.connect(self.compare_texts)
        
        # 结果区域
        result_group = QGroupBox("比较结果")
        result_layout = QVBoxLayout()
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.similarity_label = QLabel("相似度: -")
        self.lines1_label = QLabel("行数1: -")
        self.lines2_label = QLabel("行数2: -")
        self.chars1_label = QLabel("字符数1: -")
        self.chars2_label = QLabel("字符数2: -")
        
        stats_layout.addWidget(self.similarity_label)
        stats_layout.addWidget(self.lines1_label)
        stats_layout.addWidget(self.lines2_label)
        stats_layout.addWidget(self.chars1_label)
        stats_layout.addWidget(self.chars2_label)
        stats_layout.addStretch()
        
        # 差异显示
        self.diff_edit = QTextEdit()
        self.diff_edit.setReadOnly(True)
        self.diff_highlighter = DiffHighlighter(self.diff_edit.document())
        
        result_layout.addLayout(stats_layout)
        result_layout.addWidget(self.diff_edit)
        result_group.setLayout(result_layout)
        
        layout.addWidget(file_group)
        layout.addWidget(options_group)
        layout.addWidget(text_edit_group)
        layout.addWidget(self.compare_btn)
        layout.addWidget(result_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_text_extraction_tab(self):
        """创建文本提取选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 输入区域
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout()
        
        # 文件选择
        file_layout = QHBoxLayout()
        self.extract_file_path = QLineEdit()
        self.extract_file_path.setPlaceholderText("选择文件...")
        self.browse_extract_file_btn = QPushButton("浏览...")
        self.browse_extract_file_btn.clicked.connect(lambda: self.browse_file(self.extract_file_path))
        
        file_layout.addWidget(self.extract_file_path)
        file_layout.addWidget(self.browse_extract_file_btn)
        
        self.load_extract_file_btn = QPushButton("加载文件")
        self.load_extract_file_btn.clicked.connect(lambda: self.load_file(self.extract_file_path, self.extract_input_edit))
        
        # 提取类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("提取类型:"))
        self.extract_type_combo = QComboBox()
        self.extract_type_combo.addItems(["HTML清理", "URL提取", "邮箱提取", "电话号码提取"])
        type_layout.addWidget(self.extract_type_combo)
        type_layout.addStretch()
        
        # 输入文本框
        self.extract_input_edit = QTextEdit()
        self.extract_input_edit.setPlaceholderText("在此输入或粘贴要提取的文本...")
        
        input_layout.addLayout(file_layout)
        input_layout.addWidget(self.load_extract_file_btn)
        input_layout.addLayout(type_layout)
        input_layout.addWidget(self.extract_input_edit)
        input_group.setLayout(input_layout)
        
        # 提取按钮
        self.extract_btn = QPushButton("提取文本")
        self.extract_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.extract_btn.clicked.connect(self.extract_text)
        
        # 结果区域
        result_group = QGroupBox("提取结果")
        result_layout = QVBoxLayout()
        
        self.extract_result_edit = QTextEdit()
        self.extract_result_edit.setReadOnly(True)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.copy_extract_btn = QPushButton("复制结果")
        self.copy_extract_btn.clicked.connect(self.copy_extract_result)
        
        self.save_extract_btn = QPushButton("保存结果")
        self.save_extract_btn.clicked.connect(self.save_extract_result)
        
        action_layout.addWidget(self.copy_extract_btn)
        action_layout.addWidget(self.save_extract_btn)
        action_layout.addStretch()
        
        result_layout.addWidget(self.extract_result_edit)
        result_layout.addLayout(action_layout)
        result_group.setLayout(result_layout)
        
        layout.addWidget(input_group)
        layout.addWidget(self.extract_btn)
        layout.addWidget(result_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_markdown_conversion_tab(self):
        """创建Markdown转换选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        if not MARKDOWN_AVAILABLE:
            # 显示安装提示
            warning_layout = QVBoxLayout()
            warning_label = QLabel(
                "Markdown转换功能需要安装markdown库\n\n"
                "请运行: pip install markdown\n\n"
                "安装后重启应用程序"
            )
            warning_label.setAlignment(Qt.AlignCenter)
            warning_label.setStyleSheet("color: #e74c3c; font-size: 14px;")
            warning_layout.addWidget(warning_label)
            widget.setLayout(warning_layout)
            return widget
        
        # 输入区域
        input_group = QGroupBox("Markdown输入")
        input_layout = QVBoxLayout()
        
        # 文件选择
        file_layout = QHBoxLayout()
        self.md_file_path = QLineEdit()
        self.md_file_path.setPlaceholderText("选择Markdown文件...")
        self.browse_md_file_btn = QPushButton("浏览...")
        self.browse_md_file_btn.clicked.connect(lambda: self.browse_file(self.md_file_path, "Markdown文件 (*.md *.markdown);;所有文件 (*)"))
        
        file_layout.addWidget(self.md_file_path)
        file_layout.addWidget(self.browse_md_file_btn)
        
        self.load_md_file_btn = QPushButton("加载文件")
        self.load_md_file_btn.clicked.connect(lambda: self.load_file(self.md_file_path, self.md_input_edit))
        
        # 输出格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.md_format_combo = QComboBox()
        self.md_format_combo.addItems(["HTML", "纯文本"])
        format_layout.addWidget(self.md_format_combo)
        format_layout.addStretch()
        
        # 输入文本框
        self.md_input_edit = QTextEdit()
        self.md_input_edit.setPlaceholderText("在此输入或粘贴Markdown文本...")
        
        input_layout.addLayout(file_layout)
        input_layout.addWidget(self.load_md_file_btn)
        input_layout.addLayout(format_layout)
        input_layout.addWidget(self.md_input_edit)
        input_group.setLayout(input_layout)
        
        # 转换按钮
        self.convert_md_btn = QPushButton("转换Markdown")
        self.convert_md_btn.setStyleSheet(
            "QPushButton { background-color: #9b59b6; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #8e44ad; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.convert_md_btn.clicked.connect(self.convert_markdown)
        
        # 结果区域
        result_group = QGroupBox("转换结果")
        result_layout = QVBoxLayout()
        
        # 创建选项卡显示不同格式的结果
        self.md_result_tabs = QTabWidget()
        
        # HTML预览选项卡
        self.html_preview = QWebEngineView()
        self.html_preview.setHtml("<p>HTML预览将显示在这里</p>")
        self.md_result_tabs.addTab(self.html_preview, "HTML预览")
        
        # 源代码选项卡
        self.md_source_edit = QTextEdit()
        self.md_source_edit.setReadOnly(True)
        self.md_result_tabs.addTab(self.md_source_edit, "源代码")
        
        # 纯文本选项卡
        self.md_plain_edit = QTextEdit()
        self.md_plain_edit.setReadOnly(True)
        self.md_result_tabs.addTab(self.md_plain_edit, "纯文本")
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.copy_md_btn = QPushButton("复制结果")
        self.copy_md_btn.clicked.connect(self.copy_md_result)
        
        self.save_md_btn = QPushButton("保存结果")
        self.save_md_btn.clicked.connect(self.save_md_result)
        
        action_layout.addWidget(self.copy_md_btn)
        action_layout.addWidget(self.save_md_btn)
        action_layout.addStretch()
        
        result_layout.addWidget(self.md_result_tabs)
        result_layout.addLayout(action_layout)
        result_group.setLayout(result_layout)
        
        layout.addWidget(input_group)
        layout.addWidget(self.convert_md_btn)
        layout.addWidget(result_group)
        
        widget.setLayout(layout)
        return widget
    
    def browse_file(self, line_edit, filter="所有文件 (*)"):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter)
        if file_path:
            line_edit.setText(file_path)
    
    def load_file(self, path_edit, text_edit):
        """加载文件内容"""
        file_path = path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "错误", "请先选择文件")
            return
            
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件不存在")
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                text_edit.setPlainText(content)
                
            self.status_label.setText(f"已加载文件: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取文件失败: {str(e)}")
    
    def compare_texts(self):
        """比较文本"""
        text1 = self.text1_edit.toPlainText().strip()
        text2 = self.text2_edit.toPlainText().strip()
        
        if not text1 or not text2:
            QMessageBox.warning(self, "错误", "请输入要比较的文本")
            return
        
        # 禁用按钮，显示进度
        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在比较文本...")
        
        # 启动比较线程
        self.worker_thread = TextProcessingThread(
            "compare_texts",
            text1=text1,
            text2=text2,
            ignore_case=self.ignore_case_check.isChecked(),
            ignore_whitespace=self.ignore_whitespace_check.isChecked()
        )
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_compare_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def handle_compare_completed(self, message, result_data):
        """处理比较完成"""
        # 更新统计信息
        self.similarity_label.setText(f"相似度: {result_data['similarity']:.2f}%")
        self.lines1_label.setText(f"行数1: {result_data['lines1']}")
        self.lines2_label.setText(f"行数2: {result_data['lines2']}")
        self.chars1_label.setText(f"字符数1: {result_data['chars1']}")
        self.chars2_label.setText(f"字符数2: {result_data['chars2']}")
        
        # 显示差异
        diff_text = '\n'.join(result_data['diff'])
        self.diff_edit.setPlainText(diff_text)
        
        self.status_label.setText(message)
        QMessageBox.information(self, "完成", message)
    
    def extract_text(self):
        """提取文本"""
        source_text = self.extract_input_edit.toPlainText().strip()
        extract_type = self.extract_type_combo.currentText()
        
        if not source_text:
            QMessageBox.warning(self, "错误", "请输入要提取的文本")
            return
        
        # 映射提取类型
        type_map = {
            "HTML清理": "html",
            "URL提取": "urls",
            "邮箱提取": "emails",
            "电话号码提取": "phones"
        }
        
        extract_type_key = type_map.get(extract_type, "html")
        
        # 禁用按钮，显示进度
        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在提取文本...")
        
        # 启动提取线程
        self.worker_thread = TextProcessingThread(
            "extract_text",
            source_text=source_text,
            extract_type=extract_type_key
        )
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_extract_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def handle_extract_completed(self, message, result_data):
        """处理提取完成"""
        # 显示提取结果
        self.extract_result_edit.setPlainText(result_data['result'])
        
        self.status_label.setText(message)
        QMessageBox.information(self, "完成", message)
    
    def convert_markdown(self):
        """转换Markdown"""
        markdown_text = self.md_input_edit.toPlainText().strip()
        output_format = self.md_format_combo.currentText().lower()
        
        if not markdown_text:
            QMessageBox.warning(self, "错误", "请输入Markdown文本")
            return
        
        # 禁用按钮，显示进度
        self.convert_md_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在转换Markdown...")
        
        # 启动转换线程
        self.worker_thread = TextProcessingThread(
            "convert_markdown",
            markdown_text=markdown_text,
            output_format=output_format
        )
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_markdown_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def handle_markdown_completed(self, message, result_data):
        """处理Markdown转换完成"""
        result = result_data['result']
        format = result_data['format']
        
        # 显示结果
        if format == 'html':
            self.md_source_edit.setPlainText(result)
            self.html_preview.setHtml(result)
            self.md_result_tabs.setCurrentIndex(0)  # 切换到HTML预览
        else:
            self.md_plain_edit.setPlainText(result)
            self.md_result_tabs.setCurrentIndex(2)  # 切换到纯文本
        
        self.status_label.setText(message)
        QMessageBox.information(self, "完成", message)
    
    def copy_extract_result(self):
        """复制提取结果"""
        result = self.extract_result_edit.toPlainText()
        if result:
            clipboard = QApplication.clipboard()
            clipboard.setText(result)
            self.status_label.setText("结果已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "没有可复制的内容")
    
    def save_extract_result(self):
        """保存提取结果"""
        result = self.extract_result_edit.toPlainText()
        if not result:
            QMessageBox.warning(self, "提示", "没有可保存的内容")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                self.status_label.setText(f"结果已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def copy_md_result(self):
        """复制Markdown转换结果"""
        current_tab = self.md_result_tabs.currentIndex()
        if current_tab == 0:  # HTML预览
            result = self.md_source_edit.toPlainText()
        elif current_tab == 1:  # 源代码
            result = self.md_source_edit.toPlainText()
        else:  # 纯文本
            result = self.md_plain_edit.toPlainText()
            
        if result:
            clipboard = QApplication.clipboard()
            clipboard.setText(result)
            self.status_label.setText("结果已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "没有可复制的内容")
    
    def save_md_result(self):
        """保存Markdown转换结果"""
        current_tab = self.md_result_tabs.currentIndex()
        if current_tab == 0 or current_tab == 1:  # HTML预览或源代码
            result = self.md_source_edit.toPlainText()
            default_ext = ".html"
            filter = "HTML文件 (*.html *.htm);;所有文件 (*)"
        else:  # 纯文本
            result = self.md_plain_edit.toPlainText()
            default_ext = ".txt"
            filter = "文本文件 (*.txt);;所有文件 (*)"
            
        if not result:
            QMessageBox.warning(self, "提示", "没有可保存的内容")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", filter
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                self.status_label.setText(f"结果已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def update_progress(self, value, status):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
    
    def handle_error(self, error_msg):
        """处理错误"""
        self.status_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
    
    def task_finished(self):
        """任务完成回调"""
        self.progress_bar.setVisible(False)
        
        # 重新启用按钮
        self.compare_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.convert_md_btn.setEnabled(True)


class TextProcessorPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "文本处理工具"
        self.description = "提供文本比较、文本提取和Markdown转换功能"
        self.category = "办公工具"
        self.icon = None

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        return TextProcessorWidget()