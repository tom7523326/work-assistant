#!/bin/bash
# 卸载所有 LaunchAgent

set -e
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

ALL_PLISTS=(
    "com.workassistant.notify.morning"
    "com.workassistant.notify.midday"
    "com.workassistant.notify.afternoon"
    "com.workassistant.notify.evening"
    "com.workassistant.menubar"
)

echo "卸载工作助手系统集成..."
for label in "${ALL_PLISTS[@]}"; do
    dst="$LAUNCH_AGENTS/${label}.plist"
    launchctl unload "$dst" 2>/dev/null || true
    rm -f "$dst"
    echo "  ✓ 已移除 $label"
done

echo "✅ 卸载完成"
read -p "按回车关闭..."
