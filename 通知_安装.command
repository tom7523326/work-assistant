#!/bin/bash
# ╭──────────────────────────────────╮
# │  系统集成 · 一键安装                │
# │  · 4 个定时通知                     │
# │  · 菜单栏常驻图标（开机自启）        │
# ╰──────────────────────────────────╯

set -e
cd "$(dirname "$0")"

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS"

ALL_PLISTS=(
    "com.workassistant.notify.morning"
    "com.workassistant.notify.midday"
    "com.workassistant.notify.afternoon"
    "com.workassistant.notify.evening"
    "com.workassistant.menubar"
)

echo "═══════════════════════════════════════"
echo "  工作助手 · 系统集成安装"
echo "═══════════════════════════════════════"
echo ""

# 1. 测试通知
echo "▸ 步骤 1/3: 测试通知系统..."
/opt/homebrew/opt/python@3.12/libexec/bin/python3 "$(pwd)/通知.py" test
sleep 1
echo "  如果看到弹窗，说明通知权限正常"
echo ""

# 2. 安装 LaunchAgent

# Rewrite placeholder paths in LaunchAgent plists to this checkout
ROOT_ABS="$(pwd)"
for label in "${ALL_PLISTS[@]}"; do
    src="$(pwd)/launchd/${label}.plist"
    if [ -f "$src" ]; then
        sed -i '' "s|__WORK_ASSISTANT_ROOT__|${ROOT_ABS}|g" "$src"
    fi
done

echo "▸ 步骤 2/3: 注册 5 个后台任务..."
for label in "${ALL_PLISTS[@]}"; do
    src="$(pwd)/launchd/${label}.plist"
    dst="$LAUNCH_AGENTS/${label}.plist"

    if [ ! -f "$src" ]; then
        echo "  ⚠ 跳过（源文件不存在）: $label"
        continue
    fi

    launchctl unload "$dst" 2>/dev/null || true
    cp "$src" "$dst"
    launchctl load "$dst"
    echo "  ✓ $label"
done
echo ""

# 3. 完成
echo "▸ 步骤 3/3: 完成"
echo ""
echo "═══════════════════════════════════════"
echo "✅ 系统集成已激活"
echo ""
echo "  定时通知:"
echo "  · 08:00 晨间简报"
echo "  · 11:00 上午检查"
echo "  · 18:00 下午检查"
echo "  · 21:00 晚间复盘"
echo ""
echo "  菜单栏:"
echo "  · 顶部状态栏 📋 图标已启动"
echo "  · 开机自动启动"
echo ""
echo "如需卸载，运行: bash 通知_卸载.command"
echo "═══════════════════════════════════════"
echo ""
read -p "按回车关闭..."
