# gui/result_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt

class ResultView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    # 在init_ui方法中添加样式
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 设置样式
        self.setStyleSheet("""
            /* 表格样式 */
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                color: #2c3e50;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
            }
            
            /* 详情文本框样式 */
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 10px;
                background-color: #f8f9fa;
                color: #2c3e50;
                font-family: 'Consolas', monospace;
            }
            
            /* 分割器样式 */
            QSplitter::handle {
                background-color: #bdc3c7;
            }
        """)
        
        # 使用分割器同时显示表格和详情
        splitter = QSplitter(Qt.Vertical)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["状态码", "大小", "路径", "敏感信息", "URL"])
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.result_table.itemSelectionChanged.connect(self.show_detail)
        
        # 详情显示
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        
        splitter.addWidget(self.result_table)
        splitter.addWidget(self.detail_view)
        splitter.setSizes([300, 100])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def add_result(self, result):
        """添加扫描结果到表格"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        self.result_table.setItem(row, 0, QTableWidgetItem(str(result['status'])))
        self.result_table.setItem(row, 1, QTableWidgetItem(str(result['size'])))
        self.result_table.setItem(row, 2, QTableWidgetItem(result['path']))
        
        sensitive = ', '.join(result.get('sensitive_info', []))
        self.result_table.setItem(row, 3, QTableWidgetItem(sensitive))
        
        self.result_table.setItem(row, 4, QTableWidgetItem(result['url']))
    
    def show_detail(self):
        """显示选中项的详细信息"""
        selected_items = self.result_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        detail_text = f"URL: {self.result_table.item(row, 4).text()}\n"
        detail_text += f"状态码: {self.result_table.item(row, 0).text()}\n"
        detail_text += f"大小: {self.result_table.item(row, 1).text()} 字节\n"
        detail_text += f"路径: {self.result_table.item(row, 2).text()}\n"
        
        sensitive_info = self.result_table.item(row, 3).text()
        if sensitive_info:
            detail_text += f"敏感信息: {sensitive_info}\n"
        
        self.detail_view.setText(detail_text)
    
    def clear_results(self):
        """清空结果"""
        self.result_table.setRowCount(0)
        self.detail_view.clear()