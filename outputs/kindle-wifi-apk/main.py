#!/usr/bin/env python3
"""
Kindle WiFi 传书 App
==================
把手机变成 WiFi 传书服务器，Kindle 浏览器直接下载电子书。

使用方法:
  1. 打开 App，点击「启动服务器」
  2. 记下屏幕显示的地址 (http://手机IP:8080)
  3. 在 Kindle 浏览器打开该地址
  4. 上传或下载电子书
"""

import os
import sys
import socket
import html
import mimetypes
import shutil
import urllib.parse
import http.server
import threading
import time

# Kivy 核心
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle

# Android 权限和文件选择
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
    except ImportError:
        pass
    try:
        from plyer import filechooser
    except ImportError:
        filechooser = None
else:
    try:
        from plyer import filechooser
    except ImportError:
        filechooser = None

# ============================================================
# 配置
# ============================================================
PORT = 8080


# ============================================================
# Multipart 解析器（替代已废弃的 cgi.FieldStorage）
# ============================================================

def parse_multipart(body_bytes, boundary):
    """解析 multipart/form-data 请求体，返回 {field_name: {filename?, value}}"""
    result = {}
    if not body_bytes:
        return result
    boundary_bytes = b'--' + boundary.encode()
    parts = body_bytes.split(boundary_bytes)
    for part in parts:
        if b'Content-Disposition' not in part:
            continue
        # 找到头部和内容的边界
        idx = part.find(b'\r\n\r\n')
        if idx < 0:
            continue
        header_raw = part[:idx].decode('utf-8', errors='replace')
        data = part[idx+4:]
        # 去掉末尾的 \r\n
        if data.endswith(b'\r\n'):
            data = data[:-2]
        # 跳过空内容
        if not header_raw.strip():
            continue
        name = ''
        fname = ''
        for line in header_raw.split('\r\n'):
            if line.lower().startswith('content-disposition'):
                # 提取 name 和 filename
                for segment in line.split(';'):
                    seg = segment.strip()
                    if seg.startswith('name="'):
                        name = seg[6:-1]
                    elif seg.startswith('filename="'):
                        fname = seg[10:-1]
                break
        if name:
            result[name] = {
                'filename': fname,
                'value': data,
            }
    return result


# ============================================================
# HTTP 服务器
# ============================================================

def make_handler(books_dir):
    """创建一个 HTTP 请求处理器类绑定到指定的书籍目录。"""

    class KindleHandler(http.server.BaseHTTPRequestHandler):

        def __init__(self, *args, **kwargs):
            self.books_dir = books_dir
            super().__init__(*args, **kwargs)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            action = params.get('action', [None])[0]

            # 删除文件
            if action == 'delete':
                fname = params.get('file', [None])[0]
                if fname:
                    fpath = os.path.join(self.books_dir, os.path.basename(fname))
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                self._render_page()
                return

            # 主页
            if parsed.path in ('/', ''):
                self._render_page()
                return

            # 下载文件
            if parsed.path.startswith('/books/'):
                fname = os.path.basename(parsed.path)
                fpath = os.path.join(self.books_dir, fname)
                if not os.path.isfile(fpath):
                    self._render_page(err_msg='\u6587\u4ef6\u4e0d\u5b58\u5728')
                    return
                mime_type, _ = mimetypes.guess_type(fname)
                self.send_response(200)
                self.send_header('Content-Type', mime_type or 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(fname))
                self.send_header('Content-Length', str(os.path.getsize(fpath)))
                self.end_headers()
                with open(fpath, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
                return

            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

        def do_POST(self):
            """处理文件上传。"""
            try:
                ctype = self.headers.get('Content-Type', '')
                clen = self.headers.get('Content-Length', '0')
                if 'multipart/form-data' not in ctype:
                    self._render_page(err_msg='\u8bf7\u4f7f\u7528\u8868\u5355\u4e0a\u4f20')
                    return
                boundary = ctype.split('boundary=')[-1].strip()
                body = self.rfile.read(int(clen))
                form = parse_multipart(body, boundary)
                if 'file' not in form:
                    self._render_page(err_msg='\u8bf7\u9009\u62e9\u6587\u4ef6')
                    return
                items = form['file']
                if not isinstance(items, list):
                    items = [items]
                names = []
                for item in items:
                    fname = item.get('filename', '')
                    fval = item.get('value', b'')
                    if not fname or not fval:
                        continue
                    safe_name = os.path.basename(fname)
                    fpath = os.path.join(self.books_dir, safe_name)
                    with open(fpath, 'wb') as f:
                        f.write(fval)
                    names.append(safe_name)
                if len(names) == 1:
                    self._render_page(ok_msg='\u2713 {} \u4e0a\u4f20\u6210\u529f'.format(names[0]))
                elif len(names) > 1:
                    self._render_page(ok_msg='\u2713 \u4e0a\u4f20\u4e86 {} \u672c\u7535\u5b50\u4e66'.format(len(names)))
                else:
                    self._render_page(err_msg='\u8bf7\u9009\u62e9\u6587\u4ef6')
            except Exception as e:
                self._render_page(err_msg='\u4e0a\u4f20\u5931\u8d25: {}'.format(str(e)))

        def do_HEAD(self):
            """HEAD 请求——返回文件头部信息。"""
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith('/books/'):
                fname = os.path.basename(parsed.path)
                fpath = os.path.join(self.books_dir, fname)
                if os.path.isfile(fpath):
                    mime_type, _ = mimetypes.guess_type(fname)
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type or 'application/octet-stream')
                    self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(fname))
                    self.send_header('Content-Length', str(os.path.getsize(fpath)))
                    self.end_headers()
                    return
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

        def _render_page(self, ok_msg=None, err_msg=None):
            """渲染兼容 Kindle 的 HTML 页面。"""
            ip = local_ip()
            try:
                files = sorted(os.listdir(self.books_dir))
            except OSError:
                files = []

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()

            w = self.wfile.write
            w(HTML_HEAD.encode('utf-8'))

            # 标题
            w('<h1>\U0001F4DA Kindle \u4f20\u4e66 (App)</h1>'.encode())

            # 提示消息
            if ok_msg:
                w('<div class="msg msg-ok">{}</div>'.format(html.escape(ok_msg)).encode())
            if err_msg:
                w('<div class="msg msg-err">{}</div>'.format(html.escape(err_msg)).encode())

            # IP 卡片
            w(b'<div class="ip-box">')
            w('<div class="addr">http://{}:{}</div>'.format(ip, PORT).encode())
            w('<div class="hint">\U0001F4F1 \u624b\u673a / \U0001F4DA Kindle \u6d4f\u89c8\u5668\u6253\u5f00\u6b64\u5730\u5740</div>'.encode())
            w(b'</div>')

            # 上传卡片
            w(b'<div class="card">')
            w('<div class="card-title">\U0001F4E4 \u4e0a\u4f20\u7535\u5b50\u4e66</div>'.encode())
            w(b'<form action="/" method="post" enctype="multipart/form-data">')
            w(b'<input type="file" name="file" multiple>')
            w('<button type="submit">\U0001F4E4 \u4e0a\u4f20</button>'.encode())
            w(b'</form></div>')

            # 文件列表
            w(b'<div class="card">')
            w('<div class="card-title">\U0001F4DA \u7535\u5b50\u4e66 ({})</div>'.format(len(files)).encode())

            if files:
                w(b'<table>')
                w('<tr><th></th><th>\u6587\u4ef6\u540d</th><th></th></tr>'.encode())
                for fname in files:
                    fpath = os.path.join(self.books_dir, fname)
                    try:
                        size = os.path.getsize(fpath)
                    except OSError:
                        size = 0
                    sz = fmt_size(size)
                    encoded = urllib.parse.quote(fname)
                    icon = file_icon(fname)
                    w('<tr>'.encode())
                    w('{}'.format(icon).encode())
                    w('<td><a class="fname" href="/books/{}" download>{}</a> <span class="size">{}</span></td>'.format(
                        encoded, html.escape(fname), sz).encode())
                    w('<td><a class="btn-del" href="/?action=delete&file={}">{}</a></td>'.format(
                        encoded, '\u2716').encode())
                    w(b'</tr>')
                w(b'</table>')
            else:
                w('<div class="empty">\u6682\u65e0\u7535\u5b50\u4e66\U0001F4D6</div>'.encode())
            w(b'</div>')
            w(HTML_FOOT.encode('utf-8'))

    return KindleHandler


# ============================================================
# HTML 模板（兼容 Kindle 浏览器）
# ============================================================

HTML_HEAD = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Kindle \u4f20\u4e66 App</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,Helvetica,Arial,sans-serif;background:#f5f5f5;padding:16px;max-width:600px;margin:0 auto;color:#333;font-size:15px;line-height:1.5}
h1{font-size:18px;margin-bottom:14px;font-weight:600}
.ip-box{background:#e8f5e9;border-radius:6px;padding:14px;text-align:center;margin-bottom:14px}
.ip-box .addr{font-size:20px;font-weight:700;color:#2e7d32;word-break:break-all}
.ip-box .hint{font-size:12px;color:#555;margin-top:4px}
.card{background:#fff;border-radius:6px;padding:14px;margin-bottom:14px}
.card-title{font-size:13px;font-weight:600;color:#555;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}
input[type=file]{display:block;margin-bottom:10px;font-size:14px;width:100%}
button,.btn{background:#c0392b;color:#fff;border:none;padding:9px 0;border-radius:6px;font-size:15px;cursor:pointer;width:100%;display:block;text-align:center;text-decoration:none}
button:hover,.btn:hover{background:#a93226}
.btn-del{background:transparent;color:#999;font-size:13px;text-decoration:none;padding:2px 6px;border-radius:3px}
.btn-del:hover{background:#fdd;color:#c0392b;text-decoration:none}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;padding:8px 4px;border-bottom:2px solid #eee;color:#888;font-size:12px;font-weight:600}
td{padding:10px 4px;border-bottom:1px solid #f0f0f0;vertical-align:middle}
td:last-child{text-align:right;width:30px}
td:first-child{width:24px;text-align:center;font-size:18px}
.fname{font-weight:500;color:#333;text-decoration:none}
.fname:hover{color:#c0392b;text-decoration:underline}
.size{color:#999;font-size:12px;margin-left:6px}
.empty{text-align:center;padding:24px;color:#aaa;font-size:13px}
.msg{text-align:center;padding:10px;margin-bottom:14px;border-radius:6px;font-size:13px}
.msg-ok{background:#e8f5e9;color:#2e7d32}
.msg-err{background:#fbe9e7;color:#c0392b}
.footer{text-align:center;font-size:11px;color:#aaa;margin-top:20px;padding:10px}
@media(prefers-color-scheme:dark){body{background:#1a1a1a;color:#ddd}.card{background:#2a2a2a;border:1px solid #333}.ip-box{background:#0d2818;color:#95d5b2}.ip-box .addr{color:#95d5b2}.ip-box .hint{color:#aaa}th,.size,.card-title{color:#888}.fname{color:#ddd}.fname:hover{color:#e74c3c}.empty{color:#555}.btn-del{color:#666}.btn-del:hover{background:#3a1a1a;color:#e74c3c}td{border-color:#333}.msg-ok{background:#0d2818;color:#95d5b2}.msg-err{background:#3a1a1a;color:#ef9a9a}}
</style>
</head>
<body>'''

HTML_FOOT = '''<div class="footer">Kindle \u4f20\u4e66 App \u00b7 \u540c\u4e00 WiFi \u4e0b\u7528 Kindle \u6d4f\u89c8\u5668\u6253\u5f00</div>
</body>
</html>'''


# ============================================================
# 工具函数
# ============================================================

def local_ip():
    """获取设备局域网 IP 地址。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def fmt_size(n):
    """文件大小可读化。"""
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return '{:.1f} {}'.format(n, unit)
        n /= 1024
    return '{:.1f} GB'.format(n)


def file_icon(fname):
    """根据扩展名返回图标 emoji。"""
    ext = os.path.splitext(fname)[1].lower()
    icons = {
        '.mobi': '\U0001F4D5', '.azw': '\U0001F4D5', '.azw3': '\U0001F4D8',
        '.kfx': '\U0001F4D7', '.pdf': '\U0001F4C4', '.txt': '\U0001F4DD',
        '.epub': '\U0001F4D6',
    }
    return icons.get(ext, '\U0001F4DA')


# ============================================================
# Kivy App
# ============================================================

class KindleTransferApp(App):
    """Kindle WiFi 传书 App 主程序。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_thread = None
        self.httpd = None
        self._running = False
        self._books_dir = ''
        self._ip = ''

    def build(self):
        self.title = 'Kindle \u4f20\u4e66'
        Window.clearcolor = (0.96, 0.96, 0.96, 1)

        # 获取 IP
        self._ip = local_ip()

        # 数据目录
        self._books_dir = os.path.join(self.user_data_dir, 'books')
        try:
            os.makedirs(self._books_dir, exist_ok=True)
        except OSError:
            pass

        root = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))

        # --- 标题 ---
        title_lbl = Label(
            text='\U0001F4DA Kindle \u4f20\u4e66',
            size_hint=(1, None),
            height=dp(48),
            font_size=dp(22),
            bold=True,
            color=(0.2, 0.2, 0.2, 1),
        )
        root.add_widget(title_lbl)

        # --- 服务器状态卡片 ---
        status_box = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(180), spacing=dp(8))
        with status_box.canvas.before:
            Color(1, 1, 1, 1)
            self._status_rect = RoundedRectangle(size=(Window.width - dp(32), dp(180)), pos=(dp(16), 0), radius=[dp(8)])
        self._update_rect = lambda: setattr(self._status_rect, 'size', (Window.width - dp(32), dp(180)))
        Window.bind(on_resize=lambda *a: self._update_rect())

        self._status_lbl = Label(
            text='\u26AA \u670d\u52a1\u5668\u672a\u542f\u52a8',
            size_hint=(1, None),
            height=dp(28),
            font_size=dp(14),
            color=(0.5, 0.5, 0.5, 1),
        )
        status_box.add_widget(self._status_lbl)

        self._addr_lbl = Label(
            text='http://{}:{}'.format(self._ip, PORT),
            size_hint=(1, None),
            height=dp(36),
            font_size=dp(20),
            bold=True,
            color=(0.18, 0.49, 0.20, 1),
            markup=True,
        )
        status_box.add_widget(self._addr_lbl)

        self._toggle_btn = Button(
            text='\u25B6 \u542f\u52a8\u670d\u52a1\u5668',
            size_hint=(0.7, None),
            height=dp(46),
            pos_hint={'center_x': 0.5},
            background_color=(0.75, 0.22, 0.17, 1),
            color=(1, 1, 1, 1),
            font_size=dp(16),
        )
        self._toggle_btn.bind(on_press=self._on_toggle)
        status_box.add_widget(self._toggle_btn)

        root.add_widget(status_box)

        # --- 底部提示 ---
        hint_lbl = Label(
            text='\U0001F4F1 \u540c\u4e00 WiFi \u4e0b\u7528 Kindle \u6d4f\u89c8\u5668\u6253\u5f00\u4e0a\u65b9\u5730\u5740',
            size_hint=(1, None),
            height=dp(24),
            font_size=dp(12),
            color=(0.5, 0.5, 0.5, 1),
        )
        root.add_widget(hint_lbl)

        # --- 文件列表 ---
        file_header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(32))
        self._file_count_lbl = Label(
            text='\U0001F4DA \u7535\u5b50\u4e66 (0)',
            size_hint=(0.6, 1),
            font_size=dp(14),
            bold=True,
            color=(0.3, 0.3, 0.3, 1),
            halign='left',
        )
        self._file_count_lbl.bind(size=lambda *a: setattr(self._file_count_lbl, 'text_size', (self._file_count_lbl.width, None)))
        file_header.add_widget(self._file_count_lbl)

        add_btn = Button(
            text='\u2795 \u6dfb\u52a0',
            size_hint=(0.3, 1),
            font_size=dp(12),
            background_color=(0.75, 0.22, 0.17, 1),
            color=(1, 1, 1, 1),
        )
        add_btn.bind(on_press=self._on_add_file)
        file_header.add_widget(add_btn)
        root.add_widget(file_header)

        # 文件列表（可滚动）
        self._file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self._file_list.bind(minimum_height=self._file_list.setter('height'))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self._file_list)
        root.add_widget(scroll)

        # 定时刷新文件列表
        Clock.schedule_interval(self._refresh_file_list, 3)

        # Android 权限请求
        if platform == 'android':
            try:
                request_permissions([
                    Permission.INTERNET,
                    Permission.ACCESS_WIFI_STATE,
                    Permission.ACCESS_NETWORK_STATE,
                ])
            except Exception:
                pass

        return root

    def _on_toggle(self, btn):
        if self._running:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        if self._running:
            return

        books_dir = self._books_dir

        def server_task():
            handler = make_handler(books_dir)
            try:
                self.httpd = http.server.HTTPServer(('0.0.0.0', PORT), handler)
                self.httpd.serve_forever()
            except OSError as e:
                Clock.schedule_once(lambda dt: self._show_error('\u7aef\u53e3 {} \u88ab\u5360\u7528'.format(PORT)))
                return
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error('\u670d\u52a1\u5668\u9519\u8bef: {}'.format(str(e))))

        self.server_thread = threading.Thread(target=server_task, daemon=True)
        self.server_thread.start()

        self._running = True
        self._update_ui_state()

    def _stop_server(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd = None
        self._running = False
        self._update_ui_state()

    def _update_ui_state(self):
        if self._running:
            self._status_lbl.text = '\U0001F7E2 \u670d\u52a1\u5668\u8fd0\u884c\u4e2d'
            self._status_lbl.color = (0.18, 0.49, 0.20, 1)
            self._toggle_btn.text = '\u25A0 \u505c\u6b62\u670d\u52a1\u5668'
            self._toggle_btn.background_color = (0.5, 0.5, 0.5, 1)
        else:
            self._status_lbl.text = '\u26AA \u670d\u52a1\u5668\u672a\u542f\u52a8'
            self._status_lbl.color = (0.5, 0.5, 0.5, 1)
            self._toggle_btn.text = '\u25B6 \u542f\u52a8\u670d\u52a1\u5668'
            self._toggle_btn.background_color = (0.75, 0.22, 0.17, 1)

    def _show_error(self, msg):
        popup = Popup(
            title='\u9519\u8bef',
            content=Label(text=msg),
            size_hint=(0.8, 0.3),
        )
        popup.open()

    def _refresh_file_list(self, dt=None):
        """刷新文件列表显示。"""
        try:
            files = sorted(os.listdir(self._books_dir))
        except OSError:
            files = []

        self._file_count_lbl.text = '\U0001F4DA \u7535\u5b50\u4e66 ({})'.format(len(files))

        self._file_list.clear_widgets()

        if not files:
            empty_lbl = Label(
                text='\u6682\u65e0\u7535\u5b50\u4e66\n\u70b9\u51fb\u4e0a\u65b9\u300c\u2795 \u6dfb\u52a0\u300d\u6216\u5728\u7f51\u9875\u4e0a\u4f20',
                size_hint_y=None,
                height=dp(60),
                font_size=dp(13),
                color=(0.6, 0.6, 0.6, 1),
            )
            self._file_list.add_widget(empty_lbl)
            return

        for fname in files:
            fpath = os.path.join(self._books_dir, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                size = 0
            sz = fmt_size(size)
            icon = file_icon(fname)

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            with row.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(size=(Window.width - dp(32), dp(40)), pos=(dp(16), 0), radius=[dp(4)])
            self._update_rect_for_row = lambda: setattr(row.canvas.before.children[-1], 'size', (Window.width - dp(32), dp(40)))

            icon_lbl = Label(
                text=icon, size_hint=(0.1, 1), font_size=dp(20),
            )
            name_lbl = Label(
                text='{}\n{}'.format(fname, sz),
                size_hint=(0.7, 1),
                font_size=dp(13),
                halign='left',
                valign='middle',
                color=(0.3, 0.3, 0.3, 1),
            )
            name_lbl.bind(size=lambda *a: setattr(name_lbl, 'text_size', (name_lbl.width, None)))

            del_btn = Button(
                text='\u2716',
                size_hint=(0.15, 0.7),
                font_size=dp(14),
                background_color=(0.9, 0.9, 0.9, 1),
                color=(0.5, 0.5, 0.5, 1),
            )
            del_btn.fname = fname
            del_btn.bind(on_press=self._on_delete_file)

            row.add_widget(icon_lbl)
            row.add_widget(name_lbl)
            row.add_widget(del_btn)
            self._file_list.add_widget(row)

    def _on_add_file(self, btn):
        """打开文件选择器添加电子书。"""
        if filechooser:
            filechooser.open_file(
                on_selection=self._on_file_selected,
                filters=['*.mobi', '*.azw', '*.azw3', '*.kfx', '*.epub', '*.pdf', '*.txt'],
                multiple=True,
            )
        else:
            popup = Popup(
                title='\u63d0\u793a',
                content=Label(
                    text='\u8bf7\u901a\u8fc7\u7f51\u9875\u4e0a\u4f20\u529f\u80fd\u6dfb\u52a0\u7535\u5b50\u4e66\n\n'
                         '\u6253\u5f00 http://{}:{}\n\u70b9\u51fb\u300c\u4e0a\u4f20\u300d\u5373\u53ef'.format(self._ip, PORT),
                    font_size=dp(14),
                ),
                size_hint=(0.8, 0.4),
            )
            popup.open()

    def _on_file_selected(self, selection):
        """文件选择回调。"""
        if not selection:
            return
        count = 0
        for path in selection:
            try:
                fname = os.path.basename(path)
                dst = os.path.join(self._books_dir, fname)
                # 尝试直接拷贝
                with open(path, 'rb') as src:
                    with open(dst, 'wb') as dst_f:
                        shutil.copyfileobj(src, dst_f)
                count += 1
            except Exception as e:
                pass
        if count > 0:
            self._refresh_file_list()

    def _on_delete_file(self, btn):
        """删除文件。"""
        fname = getattr(btn, 'fname', '')
        if not fname:
            return
        fpath = os.path.join(self._books_dir, fname)
        try:
            os.remove(fpath)
            self._refresh_file_list()
        except OSError:
            pass


if __name__ == '__main__':
    KindleTransferApp().run()
