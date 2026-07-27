# Kindle 传书 Android App

把手机变成一个 WiFi 传书服务器，Kindle 浏览器直接下载电子书。

## 使用方法

1. 安装 APK 到 Android 手机
2. 打开 App，点击「启动服务器」
3. 确保手机和 Kindle 连接同一个 WiFi
4. 在 Kindle 的实验性浏览器打开屏幕上显示的地址
5. 上传电子书或直接下载已有文件

## 功能

- 通过浏览器上传电子书到手机（电脑、其他手机均可）
- Kindle 浏览器直接下载到本地
- 从手机本地文件选择器添加电子书
- 删除不需要的电子书
- 服务器状态实时显示
- Kindle 实验性浏览器完全兼容

## 自行构建 APK

### 环境要求

- **macOS** 需要安装 Docker（Buildozer 在 Docker 容器内构建）
- **Linux** 可直接运行 Buildozer
- Android SDK / NDK（Buildozer 会自动下载）

### 构建步骤

```bash
# 1. 安装 Buildozer（需要 Python 3）
pip install buildozer

# 2. macOS: 安装 Docker
# https://docs.docker.com/desktop/install/mac-install/

# 3. 构建（在项目目录下）
cd kindle-wifi-apk
buildozer android debug

# 4. APK 生成在
# bin/kindletransfer-1.0.0-arm64-v8a-debug.apk
```

### 直接安装

如果不想自己构建，可以在以下平台下载预构建 APK：

> 后续提供 releases 下载

## 技术细节

- 基于 **Kivy** + **Buildozer** 构建
- 嵌入式 Python HTTP 服务器（零外部依赖）
- 自定义 multipart 解析器（不依赖已废弃的 cgi 模块）
- 支持所有主流电子书格式：MOBI, AZW, AZW3, KFX, PDF, TXT, EPUB
- HTML 界面兼容 Kindle 实验性浏览器的极简渲染能力

## 许可证

MIT
