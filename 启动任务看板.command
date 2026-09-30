#!/bin/bash
# ╭──────────────────────────────────╮
# │  任务看板 · 双击启动              │
# ╰──────────────────────────────────╯

cd "$(dirname "$0")"

# 找带 tkinter 的 Python
for PYTHON in /opt/homebrew/opt/python@3.12/libexec/bin/python3 \
              /opt/homebrew/opt/python@3.13/libexec/bin/python3 \
              /opt/homebrew/bin/python3 \
              /usr/local/bin/python3 \
              /usr/bin/python3; do
    if [ -x "$PYTHON" ] && "$PYTHON" -c "import tkinter" 2>/dev/null; then
        exec "$PYTHON" "任务看板.py"
    fi
done

echo "❌ 未找到带 tkinter 的 Python"
echo "请运行: brew install python-tk@3.12"
read -p "按回车关闭..."
