import os
import glob
import shutil
from PIL import Image
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QComboBox, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog, QSpinBox,
    QListWidget, QListWidgetItem, QStackedWidget, QTabWidget,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox, QSlider, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QPixmap, QIcon
from plugins.base_plugin import BasePlugin


class ImageProcessingThread(QThread):
    """图片处理线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 当前文件名
    task_completed = pyqtSignal(str)         # 完成消息
    error_occurred = pyqtSignal(str)         # 错误消息
    files_loaded = pyqtSignal(int)           # 文件加载完成，数量

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs
        self.cancel_requested = False
        self.image_files = []

    def run(self):
        try:
            if self.task_type == "load_files":
                self.load_image_files()
            elif self.task_type == "convert_format":
                self.convert_format()
            elif self.task_type == "compress_images":
                self.compress_images()
            elif self.task_type == "resize_images":
                self.resize_images()
            elif self.task_type == "rename_images":
                self.rename_images()
        except Exception as e:
            self.error_occurred.emit(f"处理错误: {str(e)}")

    def load_image_files(self):
        """加载图片文件"""
        input_path = self.kwargs.get('input_path')
        recursive = self.kwargs.get('recursive', False)
        
        if not input_path:
            self.error_occurred.emit("请输入图片路径")
            return
            
        if not os.path.exists(input_path):
            self.error_occurred.emit("路径不存在")
            return
        
        # 收集图片文件
        self.image_files = []
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp', '*.tiff']
        
        if os.path.isfile(input_path):
            # 单个文件
            if any(input_path.lower().endswith(ext[1:]) for ext in extensions):
                self.image_files = [input_path]
        else:
            # 文件夹
            for ext in extensions:
                pattern = os.path.join(input_path, '**', ext) if recursive else os.path.join(input_path, ext)
                self.image_files.extend(glob.glob(pattern, recursive=recursive))
        
        self.files_loaded.emit(len(self.image_files))
        
    def convert_format(self):
        """转换图片格式"""
        output_format = self.kwargs.get('output_format', 'JPEG')
        output_dir = self.kwargs.get('output_dir')
        quality = self.kwargs.get('quality', 95)
        
        if not self.image_files:
            self.error_occurred.emit("没有图片文件可处理")
            return
            
        if not output_dir:
            self.error_occurred.emit("请选择输出目录")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        
        total = len(self.image_files)
        for i, img_path in enumerate(self.image_files):
            if self.cancel_requested:
                self.task_completed.emit("转换已取消")
                return
                
            try:
                self.progress_updated.emit(int(100 * i / total), f"正在处理: {os.path.basename(img_path)}")
                
                # 打开图片
                with Image.open(img_path) as img:
                    # 转换格式
                    if img.mode in ('RGBA', 'LA') and output_format.upper() == 'JPEG':
                        # JPEG不支持透明度，转换为RGB
                        img = img.convert('RGB')
                    
                    # 构建输出路径
                    filename = os.path.splitext(os.path.basename(img_path))[0]
                    output_path = os.path.join(output_dir, f"{filename}.{output_format.lower()}")
                    
                    # 保存图片
                    save_kwargs = {'format': output_format}
                    if output_format.upper() in ['JPEG', 'JPG']:
                        save_kwargs['quality'] = quality
                    elif output_format.upper() == 'WEBP':
                        save_kwargs['quality'] = quality
                    
                    img.save(output_path, **save_kwargs)
                    
            except Exception as e:
                self.error_occurred.emit(f"处理 {os.path.basename(img_path)} 时出错: {str(e)}")
        
        self.task_completed.emit(f"格式转换完成，共处理 {total} 张图片")
    
    def compress_images(self):
        """压缩图片"""
        output_dir = self.kwargs.get('output_dir')
        quality = self.kwargs.get('quality', 80)
        optimize = self.kwargs.get('optimize', True)
        
        if not self.image_files:
            self.error_occurred.emit("没有图片文件可处理")
            return
            
        if not output_dir:
            self.error_occurred.emit("请选择输出目录")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        
        total = len(self.image_files)
        for i, img_path in enumerate(self.image_files):
            if self.cancel_requested:
                self.task_completed.emit("压缩已取消")
                return
                
            try:
                self.progress_updated.emit(int(100 * i / total), f"正在处理: {os.path.basename(img_path)}")
                
                # 打开图片
                with Image.open(img_path) as img:
                    # 获取原格式
                    img_format = img.format if img.format else 'JPEG'
                    
                    # 构建输出路径
                    filename = os.path.basename(img_path)
                    output_path = os.path.join(output_dir, filename)
                    
                    # 保存压缩图片
                    save_kwargs = {
                        'format': img_format,
                        'quality': quality,
                        'optimize': optimize
                    }
                    
                    # 处理特殊格式
                    if img.mode in ('RGBA', 'LA') and img_format.upper() == 'JPEG':
                        img = img.convert('RGB')
                    
                    img.save(output_path, **save_kwargs)
                    
            except Exception as e:
                self.error_occurred.emit(f"处理 {os.path.basename(img_path)} 时出错: {str(e)}")
        
        self.task_completed.emit(f"图片压缩完成，共处理 {total} 张图片")
    
    def resize_images(self):
        """调整图片尺寸"""
        output_dir = self.kwargs.get('output_dir')
        width = self.kwargs.get('width')
        height = self.kwargs.get('height')
        keep_aspect = self.kwargs.get('keep_aspect', True)
        resize_method = self.kwargs.get('resize_method', Image.LANCZOS)
        
        if not self.image_files:
            self.error_occurred.emit("没有图片文件可处理")
            return
            
        if not output_dir:
            self.error_occurred.emit("请选择输出目录")
            return
            
        if not width and not height:
            self.error_occurred.emit("请至少指定宽度或高度")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        
        total = len(self.image_files)
        for i, img_path in enumerate(self.image_files):
            if self.cancel_requested:
                self.task_completed.emit("尺寸调整已取消")
                return
                
            try:
                self.progress_updated.emit(int(100 * i / total), f"正在处理: {os.path.basename(img_path)}")
                
                # 打开图片
                with Image.open(img_path) as img:
                    # 计算新尺寸
                    orig_width, orig_height = img.size
                    
                    if keep_aspect:
                        # 保持宽高比
                        if width and height:
                            # 同时指定宽高，按比例缩放
                            ratio = min(width / orig_width, height / orig_height)
                            new_width = int(orig_width * ratio)
                            new_height = int(orig_height * ratio)
                        elif width:
                            # 只指定宽度
                            ratio = width / orig_width
                            new_width = width
                            new_height = int(orig_height * ratio)
                        else:
                            # 只指定高度
                            ratio = height / orig_height
                            new_width = int(orig_width * ratio)
                            new_height = height
                    else:
                        # 不保持宽高比
                        new_width = width if width else orig_width
                        new_height = height if height else orig_height
                    
                    # 调整尺寸
                    resized_img = img.resize((new_width, new_height), resize_method)
                    
                    # 构建输出路径
                    filename = os.path.basename(img_path)
                    output_path = os.path.join(output_dir, filename)
                    
                    # 保存图片
                    img_format = img.format if img.format else 'JPEG'
                    resized_img.save(output_path, format=img_format)
                    
            except Exception as e:
                self.error_occurred.emit(f"处理 {os.path.basename(img_path)} 时出错: {str(e)}")
        
        self.task_completed.emit(f"尺寸调整完成，共处理 {total} 张图片")
    
    def rename_images(self):
        """重命名图片"""
        output_dir = self.kwargs.get('output_dir')
        prefix = self.kwargs.get('prefix', '')
        start_number = self.kwargs.get('start_number', 1)
        keep_original = self.kwargs.get('keep_original', False)
        
        if not self.image_files:
            self.error_occurred.emit("没有图片文件可处理")
            return
            
        if not output_dir:
            self.error_occurred.emit("请选择输出目录")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        
        total = len(self.image_files)
        current_number = start_number
        
        for i, img_path in enumerate(self.image_files):
            if self.cancel_requested:
                self.task_completed.emit("重命名已取消")
                return
                
            try:
                self.progress_updated.emit(int(100 * i / total), f"正在处理: {os.path.basename(img_path)}")
                
                # 获取文件扩展名
                _, ext = os.path.splitext(img_path)
                
                # 构建新文件名
                new_filename = f"{prefix}{current_number}{ext}"
                output_path = os.path.join(output_dir, new_filename)
                
                # 复制或移动文件
                if keep_original:
                    shutil.copy2(img_path, output_path)
                else:
                    shutil.move(img_path, output_path)
                
                current_number += 1
                    
            except Exception as e:
                self.error_occurred.emit(f"处理 {os.path.basename(img_path)} 时出错: {str(e)}")
        
        self.task_completed.emit(f"重命名完成，共处理 {total} 张图片")
    
    def cancel(self):
        self.cancel_requested = True


class ImageProcessorWidget(QWidget):
    """图片处理工具界面"""
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.image_files = []
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("图片处理工具")
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 添加各个功能选项卡
        self.tab_widget.addTab(self.create_file_selection_tab(), "文件选择")
        self.tab_widget.addTab(self.create_format_conversion_tab(), "格式转换")
        self.tab_widget.addTab(self.create_compression_tab(), "图片压缩")
        self.tab_widget.addTab(self.create_resize_tab(), "尺寸调整")
        self.tab_widget.addTab(self.create_rename_tab(), "批量重命名")
        
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
    
    def create_file_selection_tab(self):
        """创建文件选择选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 输入路径选择
        input_group = QGroupBox("选择图片或文件夹")
        input_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("选择图片文件或包含图片的文件夹...")
        self.browse_input_btn = QPushButton("浏览...")
        self.browse_input_btn.clicked.connect(self.browse_input_path)
        
        path_layout.addWidget(self.input_path)
        path_layout.addWidget(self.browse_input_btn)
        
        # 递归搜索选项
        self.recursive_check = QCheckBox("包含子文件夹")
        self.recursive_check.setChecked(True)
        
        # 加载按钮
        self.load_files_btn = QPushButton("加载图片")
        self.load_files_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        self.load_files_btn.clicked.connect(self.load_image_files)
        
        input_layout.addLayout(path_layout)
        input_layout.addWidget(self.recursive_check)
        input_layout.addWidget(self.load_files_btn)
        input_group.setLayout(input_layout)
        
        # 文件列表
        files_group = QGroupBox("图片文件列表")
        files_layout = QVBoxLayout()
        
        self.files_list = QListWidget()
        files_layout.addWidget(self.files_list)
        
        files_group.setLayout(files_layout)
        
        layout.addWidget(input_group)
        layout.addWidget(files_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_format_conversion_tab(self):
        """创建格式转换选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 输出格式选择
        format_group = QGroupBox("输出格式设置")
        format_layout = QVBoxLayout()
        
        format_select_layout = QHBoxLayout()
        format_select_layout.addWidget(QLabel("目标格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF"])
        format_select_layout.addWidget(self.format_combo)
        format_select_layout.addStretch()
        
        # 质量设置
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("质量:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        self.quality_spin.setSuffix("%")
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        
        format_layout.addLayout(format_select_layout)
        format_layout.addLayout(quality_layout)
        format_group.setLayout(format_layout)
        
        # 输出目录
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        
        output_path_layout = QHBoxLayout()
        self.convert_output_path = QLineEdit()
        self.convert_output_path.setPlaceholderText("选择输出目录...")
        self.browse_convert_output_btn = QPushButton("浏览...")
        self.browse_convert_output_btn.clicked.connect(lambda: self.browse_output_path(self.convert_output_path))
        
        output_path_layout.addWidget(self.convert_output_path)
        output_path_layout.addWidget(self.browse_convert_output_btn)
        
        output_layout.addLayout(output_path_layout)
        output_group.setLayout(output_layout)
        
        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.convert_btn.clicked.connect(self.convert_format)
        
        layout.addWidget(format_group)
        layout.addWidget(output_group)
        layout.addWidget(self.convert_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_compression_tab(self):
        """创建图片压缩选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 压缩设置
        compress_group = QGroupBox("压缩设置")
        compress_layout = QVBoxLayout()
        
        # 质量滑块
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("质量:"))
        self.compress_quality_slider = QSlider(Qt.Horizontal)
        self.compress_quality_slider.setRange(1, 100)
        self.compress_quality_slider.setValue(80)
        self.compress_quality_slider.setTickPosition(QSlider.TicksBelow)
        self.compress_quality_slider.setTickInterval(10)
        
        self.compress_quality_label = QLabel("80%")
        self.compress_quality_slider.valueChanged.connect(
            lambda v: self.compress_quality_label.setText(f"{v}%")
        )
        
        quality_layout.addWidget(self.compress_quality_slider)
        quality_layout.addWidget(self.compress_quality_label)
        
        # 优化选项
        self.optimize_check = QCheckBox("优化编码")
        self.optimize_check.setChecked(True)
        
        compress_layout.addLayout(quality_layout)
        compress_layout.addWidget(self.optimize_check)
        compress_group.setLayout(compress_layout)
        
        # 输出目录
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        
        output_path_layout = QHBoxLayout()
        self.compress_output_path = QLineEdit()
        self.compress_output_path.setPlaceholderText("选择输出目录...")
        self.browse_compress_output_btn = QPushButton("浏览...")
        self.browse_compress_output_btn.clicked.connect(lambda: self.browse_output_path(self.compress_output_path))
        
        output_path_layout.addWidget(self.compress_output_path)
        output_path_layout.addWidget(self.browse_compress_output_btn)
        
        output_layout.addLayout(output_path_layout)
        output_group.setLayout(output_layout)
        
        # 压缩按钮
        self.compress_btn = QPushButton("开始压缩")
        self.compress_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.compress_btn.clicked.connect(self.compress_images)
        
        layout.addWidget(compress_group)
        layout.addWidget(output_group)
        layout.addWidget(self.compress_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_resize_tab(self):
        """创建尺寸调整选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 尺寸设置
        resize_group = QGroupBox("尺寸设置")
        resize_layout = QGridLayout()
        
        resize_layout.addWidget(QLabel("宽度:"), 0, 0)
        self.resize_width = QSpinBox()
        self.resize_width.setRange(1, 10000)
        self.resize_width.setSpecialValueText("自动")
        resize_layout.addWidget(self.resize_width, 0, 1)
        
        resize_layout.addWidget(QLabel("高度:"), 1, 0)
        self.resize_height = QSpinBox()
        self.resize_height.setRange(1, 10000)
        self.resize_height.setSpecialValueText("自动")
        resize_layout.addWidget(self.resize_height, 1, 1)
        
        resize_layout.addWidget(QLabel("保持宽高比:"), 2, 0)
        self.keep_aspect_check = QCheckBox()
        self.keep_aspect_check.setChecked(True)
        resize_layout.addWidget(self.keep_aspect_check, 2, 1)
        
        resize_group.setLayout(resize_layout)
        
        # 输出目录
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        
        output_path_layout = QHBoxLayout()
        self.resize_output_path = QLineEdit()
        self.resize_output_path.setPlaceholderText("选择输出目录...")
        self.browse_resize_output_btn = QPushButton("浏览...")
        self.browse_resize_output_btn.clicked.connect(lambda: self.browse_output_path(self.resize_output_path))
        
        output_path_layout.addWidget(self.resize_output_path)
        output_path_layout.addWidget(self.browse_resize_output_btn)
        
        output_layout.addLayout(output_path_layout)
        output_group.setLayout(output_layout)
        
        # 调整按钮
        self.resize_btn = QPushButton("开始调整")
        self.resize_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.resize_btn.clicked.connect(self.resize_images)
        
        layout.addWidget(resize_group)
        layout.addWidget(output_group)
        layout.addWidget(self.resize_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_rename_tab(self):
        """创建批量重命名选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 重命名设置
        rename_group = QGroupBox("重命名设置")
        rename_layout = QGridLayout()
        
        rename_layout.addWidget(QLabel("前缀:"), 0, 0)
        self.rename_prefix = QLineEdit()
        self.rename_prefix.setPlaceholderText("输入文件名前缀...")
        rename_layout.addWidget(self.rename_prefix, 0, 1)
        
        rename_layout.addWidget(QLabel("起始编号:"), 1, 0)
        self.start_number = QSpinBox()
        self.start_number.setRange(1, 9999)
        self.start_number.setValue(1)
        rename_layout.addWidget(self.start_number, 1, 1)
        
        rename_layout.addWidget(QLabel("保留原文件:"), 2, 0)
        self.keep_original_check = QCheckBox()
        self.keep_original_check.setChecked(True)
        rename_layout.addWidget(self.keep_original_check, 2, 1)
        
        rename_group.setLayout(rename_layout)
        
        # 输出目录
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        
        output_path_layout = QHBoxLayout()
        self.rename_output_path = QLineEdit()
        self.rename_output_path.setPlaceholderText("选择输出目录...")
        self.browse_rename_output_btn = QPushButton("浏览...")
        self.browse_rename_output_btn.clicked.connect(lambda: self.browse_output_path(self.rename_output_path))
        
        output_path_layout.addWidget(self.rename_output_path)
        output_path_layout.addWidget(self.browse_rename_output_btn)
        
        output_layout.addLayout(output_path_layout)
        output_group.setLayout(output_layout)
        
        # 重命名按钮
        self.rename_btn = QPushButton("开始重命名")
        self.rename_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.rename_btn.clicked.connect(self.rename_images)
        
        layout.addWidget(rename_group)
        layout.addWidget(output_group)
        layout.addWidget(self.rename_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def browse_input_path(self):
        """浏览输入路径"""
        # 选择文件或文件夹
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片文件", "", "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff);;所有文件 (*)"
        )
        
        if file_path:
            self.input_path.setText(file_path)
        else:
            # 如果用户取消了文件选择，尝试选择文件夹
            dir_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
            if dir_path:
                self.input_path.setText(dir_path)
    
    def browse_output_path(self, line_edit):
        """浏览输出路径"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            line_edit.setText(dir_path)
    
    def load_image_files(self):
        """加载图片文件"""
        input_path = self.input_path.text().strip()
        recursive = self.recursive_check.isChecked()
        
        if not input_path:
            QMessageBox.warning(self, "错误", "请输入图片路径")
            return
        
        # 禁用按钮，显示进度
        self.load_files_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在加载图片文件...")
        
        # 启动加载线程
        self.worker_thread = ImageProcessingThread(
            "load_files",
            input_path=input_path,
            recursive=recursive
        )
        self.worker_thread.files_loaded.connect(self.handle_files_loaded)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def handle_files_loaded(self, count):
        """处理文件加载完成"""
        self.files_list.clear()
        
        if count == 0:
            self.status_label.setText("未找到图片文件")
            return
            
        # 显示文件列表
        for img_path in self.worker_thread.image_files:
            item = QListWidgetItem(os.path.basename(img_path))
            item.setData(Qt.UserRole, img_path)  # 存储完整路径
            self.files_list.addItem(item)
        
        self.status_label.setText(f"找到 {count} 张图片")
        
        # 启用所有处理按钮
        self.convert_btn.setEnabled(True)
        self.compress_btn.setEnabled(True)
        self.resize_btn.setEnabled(True)
        self.rename_btn.setEnabled(True)
    
    def convert_format(self):
        """转换图片格式"""
        if not self.worker_thread or not self.worker_thread.image_files:
            QMessageBox.warning(self, "错误", "请先加载图片文件")
            return
            
        output_dir = self.convert_output_path.text().strip()
        output_format = self.format_combo.currentText()
        quality = self.quality_spin.value()
        
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择输出目录")
            return
        
        # 禁用按钮，显示进度
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("开始转换图片格式...")
        
        # 启动转换线程
        self.worker_thread = ImageProcessingThread(
            "convert_format",
            output_dir=output_dir,
            output_format=output_format,
            quality=quality
        )
        self.worker_thread.image_files = self.worker_thread.image_files  # 传递文件列表
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_task_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def compress_images(self):
        """压缩图片"""
        if not self.worker_thread or not self.worker_thread.image_files:
            QMessageBox.warning(self, "错误", "请先加载图片文件")
            return
            
        output_dir = self.compress_output_path.text().strip()
        quality = self.compress_quality_slider.value()
        optimize = self.optimize_check.isChecked()
        
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择输出目录")
            return
        
        # 禁用按钮，显示进度
        self.compress_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("开始压缩图片...")
        
        # 启动压缩线程
        self.worker_thread = ImageProcessingThread(
            "compress_images",
            output_dir=output_dir,
            quality=quality,
            optimize=optimize
        )
        self.worker_thread.image_files = self.worker_thread.image_files  # 传递文件列表
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_task_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def resize_images(self):
        """调整图片尺寸"""
        if not self.worker_thread or not self.worker_thread.image_files:
            QMessageBox.warning(self, "错误", "请先加载图片文件")
            return
            
        output_dir = self.resize_output_path.text().strip()
        width = self.resize_width.value() if self.resize_width.value() > 0 else None
        height = self.resize_height.value() if self.resize_height.value() > 0 else None
        keep_aspect = self.keep_aspect_check.isChecked()
        
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择输出目录")
            return
            
        if not width and not height:
            QMessageBox.warning(self, "错误", "请至少指定宽度或高度")
            return
        
        # 禁用按钮，显示进度
        self.resize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("开始调整图片尺寸...")
        
        # 启动调整线程
        self.worker_thread = ImageProcessingThread(
            "resize_images",
            output_dir=output_dir,
            width=width,
            height=height,
            keep_aspect=keep_aspect
        )
        self.worker_thread.image_files = self.worker_thread.image_files  # 传递文件列表
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_task_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def rename_images(self):
        """重命名图片"""
        if not self.worker_thread or not self.worker_thread.image_files:
            QMessageBox.warning(self, "错误", "请先加载图片文件")
            return
            
        output_dir = self.rename_output_path.text().strip()
        prefix = self.rename_prefix.text().strip()
        start_number = self.start_number.value()
        keep_original = self.keep_original_check.isChecked()
        
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择输出目录")
            return
        
        # 禁用按钮，显示进度
        self.rename_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("开始重命名图片...")
        
        # 启动重命名线程
        self.worker_thread = ImageProcessingThread(
            "rename_images",
            output_dir=output_dir,
            prefix=prefix,
            start_number=start_number,
            keep_original=keep_original
        )
        self.worker_thread.image_files = self.worker_thread.image_files  # 传递文件列表
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.task_completed.connect(self.handle_task_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.task_finished)
        self.worker_thread.start()
    
    def update_progress(self, value, filename):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(filename)
    
    def handle_task_completed(self, message):
        """处理任务完成"""
        self.status_label.setText(message)
        QMessageBox.information(self, "完成", message)
    
    def handle_error(self, error_msg):
        """处理错误"""
        self.status_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
    
    def task_finished(self):
        """任务完成回调"""
        self.progress_bar.setVisible(False)
        
        # 重新启用加载按钮
        self.load_files_btn.setEnabled(True)
        
        # 如果文件已加载，启用处理按钮
        if self.worker_thread and self.worker_thread.image_files:
            self.convert_btn.setEnabled(True)
            self.compress_btn.setEnabled(True)
            self.resize_btn.setEnabled(True)
            self.rename_btn.setEnabled(True)


class ImageProcessorPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "图片处理工具"
        self.description = "提供图片格式转换、压缩、尺寸调整和批量重命名功能"
        self.category = "办公工具"
        self.icon = None

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        return ImageProcessorWidget()