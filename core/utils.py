import os
import sys
import subprocess

def open_file(path):
    """打开文件或目录"""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":  # macOS
        subprocess.call(["open", path])
    else:  # linux
        subprocess.call(["xdg-open", path])