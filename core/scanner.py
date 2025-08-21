import os
import re
import requests
import urllib3
from threading import Thread, Event
from queue import Queue
from urllib.parse import urljoin
from PyQt5.QtCore import QObject, pyqtSignal
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)

class DirectoryScanner(QObject):
    progress_signal = pyqtSignal(int, int)  # current, total
    result_signal = pyqtSignal(dict)        # 扫描结果
    log_signal = pyqtSignal(str)            # 日志消息
    finished_signal = pyqtSignal()          # 扫描完成信号
    
    def __init__(self, target, wordlist, options):
        super().__init__()
        self.target = target.rstrip('/')
        self.wordlist = wordlist
        self.options = options
        self.stop_event = Event()
        self.path_queue = Queue()
        self.found_items = []
        
        # 初始化检测模式
        self.detect_patterns = {}
        if options.get('detect_info', False):
            self.detect_patterns = {
                'api_keys': re.compile(r'(?i)(apikey|secret_key|access_key)\s*[:=]\s*[\'"][a-z0-9]{20,40}[\'"]'),
                'credentials': re.compile(r'(?i)(user|pass|login|pwd|username|password)[=:][^&\s]{3,50}'),
                'tokens': re.compile(r'(?i)eyJ[a-z0-9]{30,}\.eyJ[a-z0-9]{30,}\.[a-z0-9_-]{20,}'),
                'jdbc': re.compile(r'jdbc:mysql://[a-z0-9_]+:[a-z0-9_]+@[a-z0-9.-]+:[0-9]+/[a-z0-9_]+')
            }
    
    def run(self):
        """执行扫描任务"""
        try:
            # 生成扫描路径
            paths = self._generate_paths()
            total = len(paths)
            self.log_signal.emit(f"开始扫描: {self.target}")
            self.log_signal.emit(f"加载字典: {self.wordlist}")
            self.log_signal.emit(f"扫描路径数: {total}")
            self.log_signal.emit(f"线程数: {self.options['threads']}")
            
            # 添加路径到队列
            for path in paths:
                self.path_queue.put(path)
            
            # 创建并启动工作线程
            threads = []
            for _ in range(self.options['threads']):
                thread = Thread(target=self._worker)
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # 更新进度
            processed = 0
            while processed < total and not self.stop_event.is_set():
                processed = total - self.path_queue.qsize()
                self.progress_signal.emit(processed, total)
                Thread.sleep(0.5)
            
            # 等待所有线程完成
            for thread in threads:
                thread.join(timeout=1.0)
            
            self.log_signal.emit("扫描完成")
            self.finished_signal.emit()
            
        except Exception as e:
            self.log_signal.emit(f"扫描出错: {str(e)}")
            self.finished_signal.emit()
    
    def start(self):
        """启动扫描线程"""
        self.scan_thread = Thread(target=self.run)
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def stop(self):
        """停止扫描"""
        self.stop_event.set()
        self.log_signal.emit("正在停止扫描...")
    
    def _generate_paths(self):
        """生成扫描路径集合"""
        paths = set()
        
        # 从字典文件加载基础路径
        try:
            with open(self.wordlist) as f:
                for line in f:
                    path = line.strip()
                    if path:
                        paths.add(path)
                        
                        # 添加扩展名变体
                        for ext in self.options.get('extensions', []):
                            if '.' not in path.split('/')[-1]:  # 避免重复扩展
                                paths.add(f"{path}{ext}")
        except Exception as e:
            self.log_signal.emit(f"读取字典文件错误: {str(e)}")
            return []
        
        return list(paths)
    
    def _check_sensitive_info(self, response):
        """检测响应中的敏感信息"""
        findings = []
        for name, pattern in self.detect_patterns.items():
            if pattern.search(response.text):
                findings.append(name)
        return findings
    
    def _worker(self):
        """工作线程函数"""
        while not self.path_queue.empty() and not self.stop_event.is_set():
            path = self.path_queue.get()
            try:
                url = urljoin(self.target + '/', path.lstrip('/'))
                resp = requests.get(
                    url,
                    timeout=self.options.get('timeout', 5.0),
                    verify=not self.options.get('insecure', False),
                    allow_redirects=False
                )
                
                # 结果处理
                if resp.status_code in [200, 301, 302, 403]:
                    result = {
                        'url': url,
                        'status': resp.status_code,
                        'size': len(resp.content),
                        'path': path
                    }
                    
                    # 敏感信息检测
                    if self.detect_patterns:
                        info_found = self._check_sensitive_info(resp)
                        if info_found:
                            result['sensitive_info'] = info_found
                    
                    # 发送结果信号
                    self.result_signal.emit(result)
                    self.log_signal.emit(f"找到: {url} ({resp.status_code})")
                
            except Exception as e:
                if self.options.get('verbose', False):
                    self.log_signal.emit(f"扫描 {path} 出错: {str(e)}")
            
            finally:
                self.path_queue.task_done()