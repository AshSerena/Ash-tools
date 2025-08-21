import os
import json
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QSplitter, QProgressBar, QMessageBox, QGroupBox, 
    QCheckBox, QMenu, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from plugins.base_plugin import BasePlugin

class UnveilrUnpacker(QThread):
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    unpack_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, input_path, output_dir):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.result = {}
        self.running = True
        self.wxapkg_files = []

    def run(self):
        try:
            # 确定输入是文件还是目录
            if os.path.isfile(self.input_path) and self.input_path.endswith('.wxapkg'):
                self.wxapkg_files = [self.input_path]
                self.log_message.emit(f"开始解包单个文件: {os.path.basename(self.input_path)}")
            elif os.path.isdir(self.input_path):
                # 扫描目录中的所有wxapkg文件
                self.log_message.emit(f"开始扫描目录: {self.input_path}")
                for root, _, files in os.walk(self.input_path):
                    for file in files:
                        if file.endswith('.wxapkg'):
                            self.wxapkg_files.append(os.path.join(root, file))
                
                if not self.wxapkg_files:
                    raise ValueError("目录中没有找到.wxapkg文件")
                
                self.log_message.emit(f"找到 {len(self.wxapkg_files)} 个.wxapkg文件")
            else:
                raise ValueError("输入路径必须是.wxapkg文件或包含.wxapkg文件的目录")
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 获取 unveilr 工具的路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            unveilr_path = os.path.join(base_dir, "tools", "unveilr.exe")
            
            if not os.path.exists(unveilr_path):
                raise FileNotFoundError(f"未找到 unveilr 工具: {unveilr_path}")
            
            # 处理所有wxapkg文件
            total_files = len(self.wxapkg_files)
            for idx, wxapkg_file in enumerate(self.wxapkg_files):
                if not self.running:
                    self.log_message.emit("解包已中止")
                    return
                
                self.log_message.emit(f"处理文件 {idx+1}/{total_files}: {os.path.basename(wxapkg_file)}")
                
                # 构建命令
                cmd = [unveilr_path, wxapkg_file, "-o", self.output_dir]
                self.log_message.emit(f"执行命令: {' '.join(cmd)}")
                
                # 运行 unveilr
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True
                )
                
                # 处理输出
                if result.returncode == 0:
                    self.log_message.emit(f"文件 {os.path.basename(wxapkg_file)} 解包成功!")
                    self.log_message.emit("unveilr 输出:")
                    self.log_message.emit(result.stdout)
                else:
                    error_msg = f"文件 {os.path.basename(wxapkg_file)} 解包失败! 错误代码: {result.returncode}"
                    self.log_message.emit(error_msg)
                    self.log_message.emit("错误输出:")
                    self.log_message.emit(result.stderr)
                
                # 更新进度
                progress = int(100 * (idx + 1) / total_files)
                self.progress.emit(progress)
            
            # 构建结果
            extracted_files = self.scan_output_directory()
            self.result = {
                'source_dir': self.output_dir,
                'files': extracted_files,
                'app_info': self.parse_app_info(extracted_files)
            }
            self.unpack_finished.emit(self.result)
            self.log_message.emit("所有文件解包完成!")
                
        except Exception as e:
            error_msg = f"解包出错: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            import traceback
            self.log_message.emit(traceback.format_exc())

    def scan_output_directory(self):
        """扫描输出目录，获取所有文件信息"""
        self.log_message.emit("扫描输出目录...")
        extracted_files = []
        
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.output_dir)
                
                extracted_files.append({
                    'name': rel_path,
                    'size': os.path.getsize(file_path),
                    'path': file_path
                })
        
        self.log_message.emit(f"找到 {len(extracted_files)} 个文件")
        return extracted_files

    def parse_app_info(self, files):
        """解析小程序信息"""
        app_info = {}
        
        # 尝试从不同文件中获取小程序信息
        app_info_files = ['app.json', 'app-config.json', 'config.json', 'project.config.json', 'game.json']
        
        for info_file in app_info_files:
            app_json = next((f for f in files if f['name'] == info_file), None)
            if app_json:
                try:
                    with open(app_json['path'], 'r', encoding='utf-8') as f:
                        app_data = json.load(f)
                        
                        # 提取基本信息
                        app_info['name'] = app_data.get('window', {}).get('navigationBarTitleText', 
                                  app_data.get('gameName', '未知小程序'))
                        app_info['pages'] = app_data.get('pages', app_data.get('gamePages', []))
                        app_info['version'] = app_data.get('version', '未知版本')
                        
                        # 提取更多信息
                        app_info['appid'] = app_data.get('appid', app_data.get('gameAppid', ''))
                        app_info['description'] = app_data.get('description', '')
                        app_info['sitemap'] = app_data.get('sitemapLocation', '')
                        
                        # 如果找到有效信息，停止搜索
                        if app_info['name'] != '未知小程序':
                            break
                except Exception as e:
                    self.log_message.emit(f"解析{info_file}失败: {str(e)}")
        
        # 如果基本信息未找到，尝试从其他文件获取
        if not app_info.get('name'):
            for file_info in files:
                if file_info['name'].endswith('.json'):
                    try:
                        with open(file_info['path'], 'r', encoding='utf-8') as f:
                            data = f.read(1024)  # 只读取前1024字节
                            if '"appid"' in data or '"pages"' in data:
                                with open(file_info['path'], 'r', encoding='utf-8') as full_f:
                                    app_data = json.load(full_f)
                                    app_info['name'] = app_data.get('window', {}).get('navigationBarTitleText', '未知小程序')
                                    app_info['pages'] = app_data.get('pages', [])
                                    app_info['version'] = app_data.get('version', '未知版本')
                                    app_info['appid'] = app_data.get('appid', '')
                                    break
                    except:
                        continue
        
        return app_info

    def stop(self):
        self.running = False

class WxAppUnpackerPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "微信小程序逆向"
        self.description = "使用 unveilr 工具解包微信小程序 .wxapkg 文件"
        self.icon = None
        self.category = "渗透工具"  # 添加分类属性

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        return WxAppUnpackerWidget()

class WxAppUnpackerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.output_dir = os.path.expanduser("~/wxapp_unpacked")
        self.input_path = ""
        self.unpacker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 输入选择区域
        input_layout = QHBoxLayout()
        self.input_label = QLabel("输入路径:")
        self.input_input = QLineEdit()
        self.input_input.setPlaceholderText("选择.wxapkg文件或包含多个文件的目录...")
        self.browse_file_btn = QPushButton("选择文件")
        self.browse_file_btn.clicked.connect(self.browse_file)
        self.browse_dir_btn = QPushButton("选择目录")
        self.browse_dir_btn.clicked.connect(self.browse_directory)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_input)
        input_layout.addWidget(self.browse_file_btn)
        input_layout.addWidget(self.browse_dir_btn)
        
        # 输出目录区域
        output_layout = QHBoxLayout()
        self.output_label = QLabel("输出目录:")
        self.output_input = QLineEdit(self.output_dir)
        self.output_browse_btn = QPushButton("浏览...")
        self.output_browse_btn.clicked.connect(self.browse_output)
        
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_browse_btn)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout()
        
        self.auto_open_check = QCheckBox("解包后自动打开目录")
        self.auto_open_check.setChecked(True)
        
        advanced_layout.addWidget(self.auto_open_check)
        advanced_group.setLayout(advanced_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.unpack_btn = QPushButton("开始解包")
        self.unpack_btn.clicked.connect(self.start_unpack)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_unpack)
        self.open_btn = QPushButton("打开输出目录")
        self.open_btn.clicked.connect(self.open_output_dir)
        self.open_btn.setEnabled(False)
        
        control_layout.addWidget(self.unpack_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.open_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("就绪")
        
        # 小程序信息展示
        self.info_group = QGroupBox("小程序信息")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        info_layout.addWidget(self.info_text)
        self.info_group.setLayout(info_layout)
        
        # 分割器显示结果
        splitter = QSplitter(Qt.Vertical)
        
        # 文件树
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["文件", "大小", "路径"])
        self.file_tree.setColumnWidth(0, 300)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
        self.file_tree.setSortingEnabled(True)
        
        # 文件预览
        self.file_preview = QTextEdit()
        self.file_preview.setReadOnly(True)
        self.file_preview.setPlaceholderText("选择文件预览内容...")
        
        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.file_preview)
        splitter.setSizes([400, 200])
        
        # 日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("解包日志将显示在这里...")
        
        # 组装界面
        main_layout.addLayout(input_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(advanced_group)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.info_group)
        main_layout.addWidget(splitter, 5)
        main_layout.addWidget(self.log_area, 1)
        
        self.setLayout(main_layout)
        
        # 连接文件树信号
        self.file_tree.itemSelectionChanged.connect(self.preview_file)
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择.wxapkg文件", "", "微信小程序包 (*.wxapkg);;所有文件 (*)"
        )
        if file_path:
            self.input_input.setText(file_path)
    
    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择包含.wxapkg文件的目录"
        )
        if dir_path:
            self.input_input.setText(dir_path)
    
    def browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_input.setText(dir_path)
    
    def start_unpack(self):
        input_path = self.input_input.text().strip()
        output_dir = self.output_input.text().strip()
        
        if not input_path:
            self.log("错误: 请选择输入路径")
            QMessageBox.warning(self, "输入错误", "请选择.wxapkg文件或包含多个文件的目录")
            return
        
        if not output_dir:
            self.log("错误: 请选择输出目录")
            QMessageBox.warning(self, "输入错误", "请选择输出目录")
            return
        
        # 重置UI状态
        self.file_tree.clear()
        self.file_preview.clear()
        self.log_area.clear()
        self.info_text.clear()
        self.open_btn.setEnabled(False)
        
        # 创建解包器
        self.unpacker = UnveilrUnpacker(input_path, output_dir)
        self.unpacker.progress.connect(self.update_progress)
        self.unpacker.log_message.connect(self.log)
        self.unpacker.unpack_finished.connect(self.unpack_finished)
        self.unpacker.error_occurred.connect(self.handle_error)
        
        # 更新按钮状态
        self.unpack_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 开始解包
        self.unpacker.start()
    
    def stop_unpack(self):
        if self.unpacker:
            self.unpacker.stop()
            self.log("解包已停止")
            self.unpack_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def unpack_finished(self, result):
        # 更新按钮状态
        self.unpack_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.open_btn.setEnabled(True)
        
        # 显示文件树
        self.display_files(result['files'])
        
        # 显示小程序信息
        app_info = result.get('app_info', {})
        info_text = ""
        if app_info:
            info_text += f"名称: {app_info.get('name', '未知')}\n"
            info_text += f"版本: {app_info.get('version', '未知')}\n"
            info_text += f"页面数量: {len(app_info.get('pages', []))}\n"
            if app_info.get('appid'):
                info_text += f"AppID: {app_info['appid']}\n"
            if app_info.get('description'):
                info_text += f"描述: {app_info['description']}\n"
        
        if not info_text:
            info_text = "未找到小程序信息"
            
        self.info_text.setText(info_text)
        
        # 自动打开输出目录
        if self.auto_open_check.isChecked():
            self.open_output_dir()
    
    def handle_error(self, error_msg):
        QMessageBox.critical(self, "解包错误", error_msg)
    
    def display_files(self, files):
        """在树形控件中显示文件结构"""
        root_item = QTreeWidgetItem(self.file_tree, ["小程序文件", "", ""])
        root_item.setExpanded(True)
        
        # 按目录结构组织文件
        dir_structure = {}
        for file_info in files:
            path_parts = file_info['name'].split('/')
            current_level = dir_structure
            
            for part in path_parts[:-1]:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
        
        # 递归添加节点
        def add_tree_items(parent, structure, path=""):
            for name, children in structure.items():
                full_path = f"{path}/{name}" if path else name
                node = QTreeWidgetItem(parent, [name, "", full_path])
                node.setIcon(0, QIcon.fromTheme("folder"))
                add_tree_items(node, children, full_path)
        
        add_tree_items(root_item, dir_structure)
        
        # 添加文件节点
        for file_info in files:
            path_parts = file_info['name'].split('/')
            parent = root_item
            
            for part in path_parts[:-1]:
                found = False
                for i in range(parent.childCount()):
                    if parent.child(i).text(0) == part:
                        parent = parent.child(i)
                        found = True
                        break
                if not found:
                    # 如果找不到路径，创建缺失的目录
                    new_parent = QTreeWidgetItem(parent, [part, "", ""])
                    new_parent.setIcon(0, QIcon.fromTheme("folder"))
                    parent = new_parent
                    found = True
            
            size_str = self.format_size(file_info['size'])
            file_item = QTreeWidgetItem(parent, [path_parts[-1], size_str, file_info['path']])
            file_item.setData(0, Qt.UserRole, file_info['path'])  # 存储完整路径
            
            # 设置文件类型图标
            if file_info['name'].endswith('.js'):
                file_item.setIcon(0, QIcon.fromTheme("text-x-script"))
            elif file_info['name'].endswith('.json'):
                file_item.setIcon(0, QIcon.fromTheme("text-x-generic"))
            elif file_info['name'].endswith(('.png', '.jpg', '.jpeg', '.gif')):
                file_item.setIcon(0, QIcon.fromTheme("image-x-generic"))
            elif file_info['name'].endswith('.wxml'):
                file_item.setIcon(0, QIcon.fromTheme("text-html"))
        
        # 展开所有节点
        self.expand_all_items(root_item)
    
    def expand_all_items(self, item):
        """递归展开所有树节点"""
        item.setExpanded(True)
        for i in range(item.childCount()):
            self.expand_all_items(item.child(i))
    
    def show_file_context_menu(self, position):
        """显示文件右键菜单"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
        
        file_path = item.data(0, Qt.UserRole)
        if not file_path or not os.path.isfile(file_path):
            return
        
        menu = QMenu()
        
        open_action = menu.addAction(QIcon.fromTheme("document-open"), "打开文件")
        open_dir_action = menu.addAction(QIcon.fromTheme("folder-open"), "打开所在目录")
        copy_path_action = menu.addAction(QIcon.fromTheme("edit-copy"), "复制路径")
        
        action = menu.exec_(self.file_tree.viewport().mapToGlobal(position))
        
        if action == open_action:
            self.open_file(file_path)
        elif action == open_dir_action:
            self.open_file_directory(file_path)
        elif action == copy_path_action:
            self.copy_file_path(file_path)
    
    def open_file(self, file_path):
        """打开文件"""
        if os.path.exists(file_path):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.call(('xdg-open', file_path))
            except Exception as e:
                self.log(f"打开文件失败: {str(e)}")
    
    def open_file_directory(self, file_path):
        """打开文件所在目录"""
        if os.path.exists(file_path):
            try:
                dir_path = os.path.dirname(file_path)
                if os.name == 'nt':  # Windows
                    os.startfile(dir_path)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.call(('xdg-open', dir_path))
            except Exception as e:
                self.log(f"打开目录失败: {str(e)}")
    
    def copy_file_path(self, file_path):
        """复制文件路径到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        self.log(f"已复制路径: {file_path}")
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} GB"
    
    def preview_file(self):
        """预览选中的文件"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        file_path = item.data(0, Qt.UserRole)
        
        if not file_path or not os.path.isfile(file_path):
            self.file_preview.clear()
            return
        
        try:
            # 根据文件类型选择预览方式
            if file_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                # 显示图像
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.file_preview.clear()
                    self.file_preview.setHtml(f'<img src="file:///{file_path}" width="400">')
                else:
                    self.file_preview.setPlainText("无法预览图像文件")
            elif file_path.endswith(('.json', '.js', '.wxss', '.wxml', '.txt', '.html', '.css')):
                # 文本文件预览
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)  # 只预览前10000个字符
                    self.file_preview.setPlainText(content)
            elif file_path.endswith('.wasm'):
                # WebAssembly文件预览
                with open(file_path, 'rb') as f:
                    header = f.read(8)
                    hex_header = ' '.join(f'{b:02X}' for b in header)
                    self.file_preview.setPlainText(f"WebAssembly 文件头: {hex_header}")
            elif file_path.endswith('.wxapkg'):
                # 小程序包文件预览
                self.file_preview.setPlainText("这是一个小程序包文件，可以尝试解包")
            else:
                # 二进制文件预览
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    hex_header = ' '.join(f'{b:02X}' for b in header)
                    self.file_preview.setPlainText(f"文件类型: 二进制\n文件头: {hex_header}")
        except Exception as e:
            self.file_preview.setPlainText(f"无法预览文件: {str(e)}")
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = self.output_input.text().strip()
        if not output_dir:
            return
        
        if os.path.exists(output_dir):
            try:
                # 使用平台特定方式打开目录
                if os.name == 'nt':  # Windows
                    os.startfile(output_dir)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.call(('xdg-open', output_dir))
            except Exception as e:
                self.log(f"打开目录失败: {str(e)}")
        else:
            self.log("错误: 输出目录不存在")
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"解包中: {value}%")
    
    def log(self, message):
        self.log_area.append(message)
        # 自动滚动到底部
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )