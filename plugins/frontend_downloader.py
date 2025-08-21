import os
import re
import json
import time
import queue
import threading
import requests
import urllib.parse
import urllib.robotparser
import subprocess  # 添加导入
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QSplitter, QProgressBar, QMessageBox, QGroupBox, 
    QCheckBox, QMenu, QApplication, QHeaderView, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QBrush, QColor
from plugins.base_plugin import BasePlugin

class WebsiteDownloaderThread(QThread):
    progress = pyqtSignal(int, str, int, int)
    download_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, output_dir, max_depth, max_files, respect_robots):
        super().__init__()
        self.base_url = url
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.max_files = max_files
        self.respect_robots = respect_robots
        self.running = True
        self.visited = set()
        self.queue = queue.Queue()
        self.downloaded_files = []
        self.robots_parser = urllib.robotparser.RobotFileParser()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 解析基础URL
        parsed_url = urllib.parse.urlparse(self.base_url)
        self.base_domain = parsed_url.netloc
        self.base_scheme = parsed_url.scheme
        self.base_path = parsed_url.path

    def run(self):
        try:
            # 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 检查robots.txt
            if self.respect_robots:
                self.robots_parser.set_url(urllib.parse.urljoin(self.base_url, "/robots.txt"))
                try:
                    self.robots_parser.read()
                except Exception as e:
                    self.progress.emit(0, f"无法读取robots.txt: {str(e)}，继续下载...", 0, 0)
            
            # 添加起始URL到队列
            self.queue.put((self.base_url, 0))
            self.visited.add(self.base_url)
            
            # 开始下载
            total_files = 0
            while not self.queue.empty() and self.running and total_files < self.max_files:
                url, depth = self.queue.get()
                
                if depth > self.max_depth:
                    continue
                
                # 检查robots.txt是否允许访问
                if self.respect_robots and not self.robots_parser.can_fetch("*", url):
                    self.progress.emit(0, f"跳过被robots.txt禁止的URL: {url}", len(self.downloaded_files), len(self.visited))
                    continue
                
                # 下载文件
                file_info = self.download_file(url)
                if file_info:
                    self.downloaded_files.append(file_info)
                    total_files += 1
                    
                    # 解析HTML文件以获取更多链接
                    if file_info['type'] == 'html':
                        self.parse_links(file_info['local_path'], url, depth + 1)
                
                # 更新进度 - 修复括号不匹配问题
                processed = len(self.visited) - self.queue.qsize()
                total = len(self.visited) + self.queue.qsize()
                
                if total > 0:
                    progress = int((processed / total) * 100)
                else:
                    progress = 100
                
                # 获取当前文件名
                current_file = os.path.basename(file_info['local_path']) if file_info else "处理中..."
                
                self.progress.emit(
                    min(progress, 100),  # 确保不超过100%
                    f"下载: {current_file}", 
                    len(self.downloaded_files), 
                    len(self.visited)
                )
            
            # 完成下载
            self.download_finished.emit({
                'base_url': self.base_url,
                'output_dir': self.output_dir,
                'files': self.downloaded_files,
                'total_files': len(self.downloaded_files),
                'visited_urls': len(self.visited)
            })
            self.progress.emit(100, f"下载完成! 共下载 {len(self.downloaded_files)} 个文件", len(self.downloaded_files), len(self.visited))
            
        except Exception as e:
            error_msg = f"下载出错: {str(e)}"
            self.progress.emit(0, error_msg, len(self.downloaded_files), len(self.visited))
            self.error_occurred.emit(error_msg)

    def download_file(self, url):
        """下载单个文件"""
        try:
            # 获取文件路径
            parsed_url = urllib.parse.urlparse(url)
            path = parsed_url.path
            
            # 处理目录路径
            if path.endswith('/'):
                path += 'index.html'
            
            # 创建本地路径
            local_path = os.path.join(self.output_dir, path.lstrip('/'))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 下载文件
            response = self.session.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            # 保存文件
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.running:
                        return None
                    f.write(chunk)
            
            # 获取文件类型
            content_type = response.headers.get('Content-Type', '').split(';')[0]
            file_type = self.get_file_type(content_type, local_path)
            
            return {
                'url': url,
                'local_path': local_path,
                'size': os.path.getsize(local_path),
                'type': file_type,
                'content_type': content_type
            }
            
        except Exception as e:
            self.progress.emit(0, f"下载失败: {url} - {str(e)}", len(self.downloaded_files), len(self.visited))
            return None

    def get_file_type(self, content_type, path):
        """根据内容和路径获取文件类型"""
        if 'html' in content_type or path.endswith('.html') or path.endswith('.htm'):
            return 'html'
        elif 'css' in content_type or path.endswith('.css'):
            return 'css'
        elif 'javascript' in content_type or path.endswith('.js'):
            return 'javascript'
        elif 'image' in content_type:
            return 'image'
        elif 'font' in content_type:
            return 'font'
        else:
            # 根据扩展名判断
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'):
                return 'image'
            elif ext in ('.woff', '.woff2', '.ttf', '.otf'):
                return 'font'
            elif ext in ('.pdf', '.doc', '.docx', '.xls', '.xlsx'):
                return 'document'
            else:
                return 'other'

    def parse_links(self, file_path, base_url, depth):
        """解析HTML文件中的链接"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找所有链接
            for tag in soup.find_all(['a', 'link', 'script', 'img', 'source', 'iframe']):
                url = None
                if tag.name == 'a' and tag.get('href'):
                    url = tag['href']
                elif tag.name == 'link' and tag.get('href'):
                    url = tag['href']
                elif tag.name == 'script' and tag.get('src'):
                    url = tag['src']
                elif tag.name in ['img', 'source'] and tag.get('src'):
                    url = tag['src']
                elif tag.name == 'iframe' and tag.get('src'):
                    url = tag['src']
                
                if not url:
                    continue
                
                # 解析URL并规范化
                absolute_url = urllib.parse.urljoin(base_url, url)
                parsed_url = urllib.parse.urlparse(absolute_url)
                # 移除片段标识符
                absolute_url = parsed_url._replace(fragment="").geturl()
                
                # 过滤外部链接和非HTTP链接
                if parsed_url.netloc != self.base_domain:
                    continue
                if not parsed_url.scheme.startswith('http'):
                    continue
                
                # 添加到队列
                if absolute_url not in self.visited:
                    self.visited.add(absolute_url)
                    self.queue.put((absolute_url, depth))
            
        except Exception as e:
            self.progress.emit(0, f"解析链接失败: {file_path} - {str(e)}", len(self.downloaded_files), len(self.visited))

    def stop(self):
        self.running = False

class FrontendDownloaderPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "前端资源下载"
        self.description = "下载网站的前端资源文件"
        self.icon = None
        self.category = "渗透工具"  # 添加分类属性

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        # 修复：使用正确的类名 WebsiteDownloaderWidget
        return WebsiteDownloaderWidget()

class WebsiteDownloaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.output_dir = os.path.expanduser("~/website_downloads")
        self.downloader = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # URL输入区域
        url_layout = QHBoxLayout()
        self.url_label = QLabel("网站URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.url_input)
        
        # 输出目录区域
        output_layout = QHBoxLayout()
        self.output_label = QLabel("输出目录:")
        self.output_input = QLineEdit(self.output_dir)
        self.output_browse_btn = QPushButton("浏览...")
        self.output_browse_btn.clicked.connect(self.browse_output)
        
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_browse_btn)
        
        # 配置选项区域
        config_group = QGroupBox("下载配置")
        config_layout = QVBoxLayout()
        
        # 最大深度
        depth_layout = QHBoxLayout()
        self.depth_label = QLabel("最大深度:")
        self.depth_input = QLineEdit("3")
        self.depth_input.setToolTip("递归下载的最大深度")
        depth_layout.addWidget(self.depth_label)
        depth_layout.addWidget(self.depth_input)
        
        # 最大文件数
        max_files_layout = QHBoxLayout()
        self.max_files_label = QLabel("最大文件数:")
        self.max_files_input = QLineEdit("500")
        self.max_files_input.setToolTip("最多下载的文件数量")
        max_files_layout.addWidget(self.max_files_label)
        max_files_layout.addWidget(self.max_files_input)
        
        # robots.txt 尊重
        self.robots_check = QCheckBox("尊重robots.txt")
        self.robots_check.setChecked(True)
        
        config_layout.addLayout(depth_layout)
        config_layout.addLayout(max_files_layout)
        config_layout.addWidget(self.robots_check)
        config_group.setLayout(config_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(self.start_download)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_download)
        self.open_btn = QPushButton("打开输出目录")
        self.open_btn.clicked.connect(self.open_output_dir)
        self.open_btn.setEnabled(False)
        
        control_layout.addWidget(self.download_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.open_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("就绪")
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.files_label = QLabel("已下载: 0")
        self.visited_label = QLabel("已访问: 0")
        stats_layout.addWidget(self.files_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.visited_label)
        
        # 文件树
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["文件", "类型", "大小", "路径"])
        self.file_tree.setColumnWidth(0, 300)
        self.file_tree.setColumnWidth(1, 100)
        self.file_tree.setColumnWidth(2, 80)
        self.file_tree.setColumnWidth(3, 400)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
        self.file_tree.setSortingEnabled(True)
        
        # 日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("下载日志将显示在这里...")
        
        # 组装界面
        main_layout.addLayout(url_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(config_group)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(stats_layout)
        main_layout.addWidget(self.file_tree, 3)
        main_layout.addWidget(self.log_area, 1)
        
        self.setLayout(main_layout)

    def browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_input.setText(dir_path)
    
    def start_download(self):
        url = self.url_input.text().strip()
        output_dir = self.output_input.text().strip()
        
        if not url:
            self.log("错误: 请输入网站URL")
            QMessageBox.warning(self, "输入错误", "请输入网站URL")
            return
        
        if not output_dir:
            self.log("错误: 请选择输出目录")
            QMessageBox.warning(self, "输入错误", "请选择输出目录")
            return
        
        # 获取配置参数
        try:
            max_depth = int(self.depth_input.text().strip())
        except ValueError:
            max_depth = 3
        
        try:
            max_files = int(self.max_files_input.text().strip())
        except ValueError:
            max_files = 500
        
        respect_robots = self.robots_check.isChecked()
        
        # 重置UI状态
        self.file_tree.clear()
        self.log_area.clear()
        self.open_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在准备下载...")
        self.files_label.setText("已下载: 0")
        self.visited_label.setText("已访问: 0")
        
        # 创建下载器
        self.downloader = WebsiteDownloaderThread(
            url, 
            output_dir,
            max_depth,
            max_files,
            respect_robots
        )
        self.downloader.progress.connect(self.update_progress)
        self.downloader.download_finished.connect(self.download_finished)
        self.downloader.error_occurred.connect(self.handle_error)
        
        # 更新按钮状态
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 开始下载
        self.downloader.start()
    
    def stop_download(self):
        if self.downloader:
            self.downloader.stop()
            self.log("下载已停止")
            self.download_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def download_finished(self, result):
        # 更新按钮状态
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.open_btn.setEnabled(True)
        
        # 显示文件树
        self.display_files(result['files'])
        
        # 更新状态
        self.status_label.setText(f"下载完成! 共下载 {result['total_files']} 个文件")
        
    def display_files(self, files):
        """在树形控件中显示文件结构"""
        root_item = QTreeWidgetItem(self.file_tree, ["网站文件", "", "", ""])
        root_item.setExpanded(True)
        
        # 按目录结构组织文件
        dir_structure = {}
        for file_info in files:
            # 获取相对路径
            rel_path = os.path.relpath(file_info['local_path'], self.output_input.text())
            path_parts = os.path.normpath(rel_path).split(os.sep)
            
            current_level = dir_structure
            for part in path_parts[:-1]:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
        
        # 递归添加节点
        def add_tree_items(parent, structure, path=""):
            for name, children in structure.items():
                full_path = os.path.join(path, name) if path else name
                node = QTreeWidgetItem(parent, [name, "目录", "", full_path])
                node.setIcon(0, QIcon.fromTheme("folder"))
                add_tree_items(node, children, full_path)
        
        add_tree_items(root_item, dir_structure)
        
        # 添加文件节点
        for file_info in files:
            # 获取相对路径
            rel_path = os.path.relpath(file_info['local_path'], self.output_input.text())
            path_parts = os.path.normpath(rel_path).split(os.sep)
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
                    new_parent = QTreeWidgetItem(parent, [part, "目录", "", ""])
                    new_parent.setIcon(0, QIcon.fromTheme("folder"))
                    parent = new_parent
                    found = True
            
            size_str = self.format_size(file_info['size'])
            file_item = QTreeWidgetItem(parent, [
                path_parts[-1],
                file_info['type'],
                size_str,
                file_info['local_path']
            ])
            file_item.setData(0, Qt.UserRole, file_info['local_path'])  # 存储完整路径
            
            # 设置文件类型图标
            if file_info['type'] == 'html':
                file_item.setIcon(0, QIcon.fromTheme("text-html"))
            elif file_info['type'] == 'css':
                file_item.setIcon(0, QIcon.fromTheme("text-css"))
            elif file_info['type'] == 'javascript':
                file_item.setIcon(0, QIcon.fromTheme("text-x-script"))
            elif file_info['type'] == 'image':
                file_item.setIcon(0, QIcon.fromTheme("image-x-generic"))
        
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
    
    def update_progress(self, progress, message, files_count, visited_count):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.files_label.setText(f"已下载: {files_count}")
        self.visited_label.setText(f"已访问: {visited_count}")
        self.log(message)  # 将进度消息记录到日志
    
    def handle_error(self, error_msg):
        self.status_label.setText(error_msg)
        QMessageBox.critical(self, "下载错误", error_msg)
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log(f"错误: {error_msg}")
    
    def log(self, message):
        self.log_area.append(message)
        # 自动滚动到底部
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )