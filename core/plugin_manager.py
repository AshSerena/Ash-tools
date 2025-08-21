import os
import importlib
import inspect
from plugins import get_plugin_classes  # 导入插件列表

class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def load_plugins(self):
        """加载所有插件"""
        # 从插件列表加载
        for plugin_class in get_plugin_classes():
            try:
                plugin_instance = plugin_class()
                self.plugins.append(plugin_instance)
                print(f"加载插件: {plugin_instance.name}")
            except Exception as e:
                print(f"加载插件 {plugin_class.__name__} 失败: {str(e)}")
    
    def get_plugins(self):
        """获取所有插件实例"""
        return self.plugins