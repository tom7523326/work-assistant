#!/bin/bash
# 启动菜单栏常驻图标
cd "$(dirname "$0")"

# rumps 装在系统 Python 的 user site
exec /usr/bin/python3 "菜单栏.py"
