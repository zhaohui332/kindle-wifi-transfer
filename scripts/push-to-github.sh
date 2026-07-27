#!/bin/bash
# ============================================
# Kindle WiFi 传书 — GitHub 推送脚本
# ============================================
# 用法:
#   1. 浏览器打开 https://github.com/new
#      仓库名填: kindle-wifi-transfer
#      设为 Public
#      不要勾选任何初始化选项
#      点击 "Create repository"
#
#   2. 回到终端，运行此脚本
#      bash scripts/push-to-github.sh
#
#   3. 去 GitHub → Actions 标签页
#      点击 "Build Kindle WiFi APK" → "Run workflow"
#
#   4. 等 20-30 分钟 → 下载 APK 安装到手机
# ============================================

set -e

echo "========================================"
echo " Kindle WiFi 传书 — GitHub 推送"
echo "========================================"
echo ""

# 检查 git
if ! command -v git &>/dev/null; then
  echo "错误: 未安装 git。请先安装 Xcode Command Line Tools:"
  echo "  xcode-select --install"
  echo ""
  echo "然后在弹出的对话框中点击「安装」，等待完成后再运行此脚本。"
  exit 1
fi

cd "$(dirname "$0")/.."

# 初始化 git 仓库
if [ ! -d .git ]; then
  git init
  echo "[OK] git 仓库已初始化"
fi

# 设置用户信息
read -p "GitHub 用户名: " GH_USER
git config user.name "$GH_USER"
read -p "GitHub 邮箱: " GH_EMAIL
git config user.email "$GH_EMAIL"

# 添加并提交
git add .
git commit -m "初始提交: Kindle WiFi 传书应用"
echo "[OK] 已提交"

# 推送到 GitHub
echo ""
echo "开始推送... 如果未配置 SSH 密钥，会提示输入密码。"
echo "推荐使用 GitHub CLI 或 SSH Key，详见:"
echo "  https://docs.github.com/zh/authentication"
echo ""

echo "请先在浏览器创建仓库: https://github.com/new"
echo "仓库名: kindle-wifi-transfer"
echo ""
read -p "按 Enter 继续推送..."

git remote add origin "https://github.com/${GH_USER}/kindle-wifi-transfer.git"
git push -u origin main || git push -u origin master

echo ""
echo "========================================"
echo " 推送成功!"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 打开 https://github.com/${GH_USER}/kindle-wifi-transfer"
echo "  2. 点击 Actions 标签"
echo "  3. 点击 \"Build Kindle WiFi APK\" → \"Run workflow\""
echo "  4. 等待构建完成（约 20-30 分钟）"
echo "  5. 在 Actions 页面下载 APK 工件"
echo "  6. 安装到 Android 手机"
echo ""
