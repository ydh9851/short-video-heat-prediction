# -*- coding: utf-8 -*-
"""pytest 全局夹具：把算法各子模块目录加入 sys.path。

算法脚本之间通过 `sys.path.insert` + `import predict_api as P` 互相引用，
测试直接以模块方式导入，因此只需保证各模块目录在可搜索路径中。
"""
import os
import sys

ALGORITHM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for sub in ("prediction", "datasets", "attribution", "evaluation"):
    path = os.path.join(ALGORITHM_DIR, sub)
    if path not in sys.path:
        sys.path.insert(0, path)