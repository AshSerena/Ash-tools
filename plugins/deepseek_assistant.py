import os
import json
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QComboBox, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QSplitter, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QTextCursor
from plugins.base_plugin import BasePlugin

class DeepSeekThread(QThread):
    """DeepSeek API 后台线程"""
    response_received = pyqtSignal(str)  # AI 响应内容
    error_occurred = pyqtSignal(str)    # 错误信息
    progress_updated = pyqtSignal(int)   # 进度更新

    def __init__(self, api_key, model, prompt, max_tokens=2000):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.cancel_requested = False

    def run(self):
        try:
            self.progress_updated.emit(10)
            
            # DeepSeek API 端点
            url = "https://api.deepseek.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的安全专家，专门从事渗透测试和漏洞分析。"},
                    {"role": "user", "content": self.prompt}
                ],
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            self.progress_updated.emit(30)
            
            # 发送 API 请求
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            self.progress_updated.emit(70)
            
            if self.cancel_requested:
                self.response_received.emit("请求已取消")
                return
                
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API 错误: {response.status_code} - {response.text}"
                raise Exception(error_msg)
            
            # 解析响应
            data = response.json()
            ai_response = data["choices"][0]["message"]["content"].strip()
            
            self.progress_updated.emit(90)
            self.response_received.emit(ai_response)
            self.progress_updated.emit(100)
            
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"网络错误: {str(e)}")
        except KeyError:
            self.error_occurred.emit("API响应格式错误，无法解析结果")
        except Exception as e:
            self.error_occurred.emit(f"发生错误: {str(e)}")
    
    def cancel(self):
        self.cancel_requested = True


class DeepSeekWidget(QWidget):
    """DeepSeek AI 安全助手界面"""
    def __init__(self):
        super().__init__()
        self.ai_thread = None
        self.config_file = "deepseek_config.json"
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("DeepSeek 安全助手")
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 配置区域
        config_group = QGroupBox("API 配置")
        config_layout = QVBoxLayout()
        
        # API 密钥输入
        api_layout = QHBoxLayout()
        self.api_label = QLabel("DeepSeek API 密钥:")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("输入您的 DeepSeek API 密钥")
        self.api_input.setEchoMode(QLineEdit.Password)
        
        api_layout.addWidget(self.api_label)
        api_layout.addWidget(self.api_input)
        config_layout.addLayout(api_layout)
        
        # 模型选择
        model_layout = QHBoxLayout()
        self.model_label = QLabel("模型选择:")
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "deepseek-chat", 
            "deepseek-coder"
        ])
        
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_combo)
        config_layout.addLayout(model_layout)
        
        # Token 数量
        token_layout = QHBoxLayout()
        self.token_label = QLabel("最大 Token 数:")
        self.token_input = QLineEdit("2000")
        self.token_input.setMaximumWidth(80)
        
        token_layout.addWidget(self.token_label)
        token_layout.addWidget(self.token_input)
        config_layout.addLayout(token_layout)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # 输入区域
        input_group = QGroupBox("输入")
        input_layout = QVBoxLayout()
        
        # 预设提示选择
        prompt_layout = QHBoxLayout()
        self.prompt_label = QLabel("预设提示:")
        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems([
            "自定义输入",
            "漏洞分析",
            "渗透测试计划",
            "安全报告生成",
            "代码安全审查",
            "安全事件响应",
            "恶意软件分析",
            "网络流量分析"
        ])
        self.prompt_combo.currentIndexChanged.connect(self.prompt_selected)
        
        prompt_layout.addWidget(self.prompt_label)
        prompt_layout.addWidget(self.prompt_combo)
        input_layout.addLayout(prompt_layout)
        
        # 输入文本框
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("在此输入您的问题或请求...")
        self.input_edit.setMinimumHeight(150)
        input_layout.addWidget(self.input_edit)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.ask_btn = QPushButton("询问 DeepSeek")
        self.ask_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2980b9; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.ask_btn.clicked.connect(self.ask_deepseek)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #c0392b; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.cancel_btn.clicked.connect(self.cancel_request)
        self.cancel_btn.setEnabled(False)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; border: none; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #27ae60; }"
        )
        self.save_btn.clicked.connect(self.save_config)
        
        button_layout.addWidget(self.ask_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 响应区域
        response_group = QGroupBox("DeepSeek 响应")
        response_layout = QVBoxLayout()
        
        self.response_edit = QTextEdit()
        self.response_edit.setReadOnly(True)
        self.response_edit.setPlaceholderText("DeepSeek 的响应将显示在这里...")
        response_layout.addWidget(self.response_edit)
        
        # 响应操作按钮
        action_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("复制响应")
        self.copy_btn.setStyleSheet(
            "QPushButton { background-color: #9b59b6; color: white; border: none; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #8e44ad; }"
        )
        self.copy_btn.clicked.connect(self.copy_response)
        
        self.save_response_btn = QPushButton("保存到文件")
        self.save_response_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; border: none; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d35400; }"
        )
        self.save_response_btn.clicked.connect(self.save_response)
        
        self.clear_btn = QPushButton("清空响应")
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; border: none; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        self.clear_btn.clicked.connect(self.clear_response)
        
        action_layout.addWidget(self.copy_btn)
        action_layout.addWidget(self.save_response_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addStretch()
        
        response_layout.addLayout(action_layout)
        response_group.setLayout(response_layout)
        main_layout.addWidget(response_group)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 5px; border-top: 1px solid #ecf0f1;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QTextEdit {
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 5px;
                font-family: 'Consolas', monospace;
            }
        """)
    
    def load_config(self):
        """加载保存的配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    self.api_input.setText(config.get("api_key", ""))
                    self.model_combo.setCurrentText(config.get("model", "deepseek-chat"))
                    self.token_input.setText(str(config.get("max_tokens", 2000)))
                    self.status_label.setText("配置已加载")
        except Exception as e:
            self.status_label.setText(f"加载配置错误: {str(e)}")
    
    def save_config(self):
        """保存当前配置"""
        config = {
            "api_key": self.api_input.text(),
            "model": self.model_combo.currentText(),
            "max_tokens": int(self.token_input.text())
        }
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            self.status_label.setText("配置已保存")
        except Exception as e:
            self.status_label.setText(f"保存配置错误: {str(e)}")
    
    def prompt_selected(self, index):
        """预设提示选择事件"""
        if index == 0:  # 自定义输入
            self.input_edit.setPlaceholderText("在此输入您的问题或请求...")
            return
        
        prompts = {
            1: "分析以下漏洞报告，提供修复建议和缓解措施:\n\n[在此粘贴漏洞报告]",
            2: "为一个Web应用程序创建一个详细的渗透测试计划，包括测试范围、方法论、工具和技术。",
            3: "根据以下渗透测试结果生成一份专业的安全报告，包括执行摘要、详细发现、风险评级和建议:\n\n[在此粘贴测试结果]",
            4: "审查以下代码片段，识别安全漏洞并提供修复建议:\n\n[在此粘贴代码]",
            5: "为以下安全事件创建一个事件响应计划:\n\n[描述安全事件]",
            6: "分析以下恶意软件样本的行为特征和潜在危害:\n\n[恶意软件描述或哈希]",
            7: "解释以下网络流量数据包，识别潜在的安全威胁:\n\n[流量数据摘要]"
        }
        
        prompt_text = prompts.get(index, "")
        self.input_edit.setPlainText(prompt_text)
    
    def ask_deepseek(self):
        """向DeepSeek发送请求"""
        api_key = self.api_input.text()
        prompt = self.input_edit.toPlainText()
        
        if not api_key:
            QMessageBox.warning(self, "输入错误", "请输入DeepSeek API密钥")
            return
            
        if not prompt:
            QMessageBox.warning(self, "输入错误", "请输入问题或请求")
            return
            
        try:
            max_tokens = int(self.token_input.text())
            if max_tokens < 100 or max_tokens > 4000:
                raise ValueError("Token数必须在100到4000之间")
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return
        
        # 禁用按钮
        self.ask_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在与DeepSeek通信...")
        
        # 清空之前的响应
        self.response_edit.clear()
        
        # 启动AI线程
        self.ai_thread = DeepSeekThread(
            api_key,
            self.model_combo.currentText(),
            prompt,
            max_tokens
        )
        self.ai_thread.response_received.connect(self.handle_response)
        self.ai_thread.error_occurred.connect(self.handle_error)
        self.ai_thread.progress_updated.connect(self.progress_bar.setValue)
        self.ai_thread.finished.connect(self.request_finished)
        self.ai_thread.start()
    
    def cancel_request(self):
        """取消请求"""
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.cancel()
            self.status_label.setText("正在取消请求...")
            self.cancel_btn.setEnabled(False)
    
    def request_finished(self):
        """请求完成回调"""
        self.ask_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def handle_response(self, response):
        """处理DeepSeek响应"""
        # 先处理响应内容中的换行符，避免在f-string中使用反斜杠
        formatted_response = response.replace('\n', '<br>')
        
        # 设置响应文本格式
        self.response_edit.setHtml(f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; 
                        background-color: #f8f9fa; 
                        padding: 15px; 
                        border-radius: 5px;
                        border-left: 4px solid #3498db;">
                {formatted_response}
            </div>
        """)
        
        # 滚动到底部
        self.response_edit.moveCursor(QTextCursor.End)
        self.status_label.setText("DeepSeek响应已接收")
    
    def handle_error(self, error_msg):
        """处理错误信息"""
        self.response_edit.setPlainText(f"错误: {error_msg}")
        self.status_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "DeepSeek请求错误", error_msg)
    
    def copy_response(self):
        """复制响应内容"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.response_edit.toPlainText())
        self.status_label.setText("响应已复制到剪贴板")
    
    def save_response(self):
        """保存响应到文件"""
        if not self.response_edit.toPlainText():
            QMessageBox.warning(self, "保存错误", "没有可保存的内容")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存响应", "", "文本文件 (*.txt);;HTML文件 (*.html);;Markdown文件 (*.md)"
        )
        
        if not file_path:
            return
            
        try:
            content = self.response_edit.toPlainText()
            
            if file_path.endswith(".html"):
                # 先处理响应内容中的换行符，避免在f-string中使用反斜杠
                formatted_content = content.replace('\n', '<br>')
                
                content = f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>DeepSeek安全助手响应</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                        .response {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #3498db; }}
                    </style>
                </head>
                <body>
                    <h1>DeepSeek安全助手响应</h1>
                    <div class="response">{formatted_content}</div>
                </body>
                </html>
                '''
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            self.status_label.setText(f"响应已保存到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存失败: {str(e)}")
    
    def clear_response(self):
        """清空响应内容"""
        self.response_edit.clear()
        self.status_label.setText("响应已清空")


class DeepSeekPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "DeepSeek安全助手"
        self.description = "使用DeepSeek AI进行安全分析和渗透测试辅助"
        self.icon = None  # 可以添加图标路径

    def get_action(self, parent=None):
        """返回插件的动作"""
        action = super().get_action(parent)
        return action
    
    def get_widget(self):
        """返回插件界面组件"""
        return DeepSeekWidget()