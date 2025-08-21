# plugins/__init__.py
from .base_plugin import BasePlugin
from .directory_scanner import DirectoryScannerPlugin
from .security_search import SecuritySearchPlugin
from .wxapp_unpacker import WxAppUnpackerPlugin  # 添加这一行
from .sensitive_info_scanner import SensitiveInfoScannerPlugin
from .frontend_downloader import FrontendDownloaderPlugin
from .office_tools import WordToPDFPlugin, PDFToWordPlugin, ExcelExtractPlugin  # 添加办公工具插件
from .image_processor import ImageProcessorPlugin  # 添加图片处理插件
from .text_processor import TextProcessorPlugin  # 添加文本处理插件

# 注册所有插件
PLUGINS = [
    DirectoryScannerPlugin,
    SecuritySearchPlugin,
    WxAppUnpackerPlugin,  # 添加这一行
    SensitiveInfoScannerPlugin,
    FrontendDownloaderPlugin,
    WordToPDFPlugin,      # 添加Word转PDF插件
    PDFToWordPlugin,      # 添加PDF转Word插件
    ExcelExtractPlugin,    # 添加Excel数据处理插件
    ImageProcessorPlugin,  # 添加图片处理插件
    TextProcessorPlugin,  # 添加文本处理插件
]

def get_plugin_classes():
    return PLUGINS