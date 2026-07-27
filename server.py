#!/usr/bin/env python3
"""
Kindle WiFi 传书服务器
======================
在同一 WiFi 下，通过浏览器从手机/电脑传输电子书到 Kindle。
Kindle 的实验性浏览器和手机浏览器均可使用。

使用方法:
  python3 server.py

然后在 Kindle 或手机的浏览器中打开显示的地址。

支持格式: MOBI, AZW, AZW3, KFX, PDF, TXT, EPUB 等
(Kindle 原生支持 MOBI/AZW/KFX/PDF/TXT, EPUB 需先转换)
"""

import os
import sys
import socket
import html
import http.server
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore', DeprecationWarning)
    import cgi
import shutil
import urllib.parse
import mimetypes
# ============================================================
# 配置
# ============================================================
BOOKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books')
PORT = 8080

os.makedirs(BOOKS_DIR, exist_ok=True)


# ============================================================
# 工具函数
# ============================================================

def local_ip():
    """获取本机局域网 IP 地址。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def fmt_size(n):
    """文件大小可读化。"""
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} GB'


def file_icon(fname):
    """根据文件扩展名返回一个简单的图标。"""
    ext = os.path.splitext(fname)[1].lower()
    icons = {
        '.mobi': '\U0001F4D5', '.azw': '\U0001F4D5', '.azw3': '\U0001F4D8', '.kfx': '\U0001F4D7',
        '.pdf': '\U0001F4C4', '.txt': '\U0001F4DD', '.epub': '\U0001F4D6', '.html': '\U0001F310',
    }
    return icons.get(ext, '\U0001F4DA')


# ============================================================
# HTML 页面（尽可能简单以兼容 Kindle 实验性浏览器）
# ============================================================

HTML_HEAD = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Kindle 传书</title>
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
th{text-align:left;padding:8px 4px;border-bottom:2px solid #eee;color:#888;font-size:12px;font-weight:600;text-transform:uppercase}
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
<body>
'''

HTML_FOOT = '''
<div class="footer">Kindle \u4f20\u4e66 \u00b7 \u540c\u4e00 WiFi \u4e0b\u5728\u4efb\u4e00\u8bbe\u5907\u6253\u5f00\u5730\u5740\u5373\u53ef</div>
</body>
</html>'''


# ============================================================
# HTTP 请求处理器
# ============================================================

class KindleTransferHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        action = params.get('action', [None])[0]

        # --- 删除文件 ---
        if action == 'delete':
            fname = params.get('file', [None])[0]
            if fname:
                fpath = os.path.join(BOOKS_DIR, os.path.basename(fname))
                if os.path.isfile(fpath):
                    os.remove(fpath)
                self._render_page(ok_msg='\u5df2\u5220\u9664')
                return

        # --- 主页 ---
        if parsed.path in ('/', ''):
            self._render_page()
            return

        # --- 下载文件 ---
        if parsed.path.startswith('/books/'):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(BOOKS_DIR, fname)
            if not os.path.isfile(fpath):
                self._render_page(err_msg='\u6587\u4ef6\u4e0d\u5b58\u5728')
                return
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(fname)
            self.send_header('Content-Type', mime_type or 'application/octet-stream')
            self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(fname))
            self.send_header('Content-Length', str(os.path.getsize(fpath)))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with open(fpath, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'404 Not Found')

    def do_HEAD(self):
        """HEAD 请求——返回与 GET 相同的头部（不包含响应体）。"""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        action = params.get('action', [None])[0]

        # 文件下载：返回文件头部
        if parsed.path.startswith('/books/'):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(BOOKS_DIR, fname)
            if os.path.isfile(fpath):
                self.send_response(200)
                mime_type, _ = mimetypes.guess_type(fname)
                self.send_header('Content-Type', mime_type or 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(fname))
                self.send_header('Content-Length', str(os.path.getsize(fpath)))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                return

        # 其他路径：简单重定向到主页
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_POST(self):
        """\u5904\u7406\u6587\u4ef6\u4e0a\u4f20\u3002"""
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = self.headers.get('Content-Length', '0')

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type,
                    'CONTENT_LENGTH': content_length,
                }
            )

            if 'file' not in form:
                self._render_page(err_msg='\u8bf7\u9009\u62e9\u8981\u4e0a\u4f20\u7684\u6587\u4ef6')
                return

            file_items = form['file']
            if not isinstance(file_items, list):
                file_items = [file_items]

            names = []
            for file_item in file_items:
                if not file_item.filename:
                    continue
                # \u6e05\u7406\u6587\u4ef6\u540d\uff0c\u9632\u6b62\u8def\u5f84\u7a7f\u900f
                fname = os.path.basename(file_item.filename)
                fpath = os.path.join(BOOKS_DIR, fname)
                with open(fpath, 'wb') as f:
                    if hasattr(file_item.file, 'read'):
                        shutil.copyfileobj(file_item.file, f)
                    else:
                        f.write(file_item.file)
                names.append(fname)

            if len(names) == 1:
                self._render_page(ok_msg='\u2713 {} \u4e0a\u4f20\u6210\u529f'.format(names[0]))
            elif len(names) > 1:
                self._render_page(ok_msg='\u2713 \u4e0a\u4f20\u4e86 {} \u672c\u7535\u5b50\u4e66'.format(len(names)))
            else:
                self._render_page(err_msg='\u8bf7\u9009\u62e9\u8981\u4e0a\u4f20\u7684\u6587\u4ef6')

        except Exception as e:
            self._render_page(err_msg='\u4e0a\u4f20\u5931\u8d25: {}'.format(str(e)))

    def _render_page(self, ok_msg=None, err_msg=None):
        """\u6e32\u67d3\u5b8c\u6574\u9875\u9762\u3002"""
        ip = local_ip()
        files = sorted(os.listdir(BOOKS_DIR))

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

        w = self.wfile.write
        w(HTML_HEAD.encode('utf-8'))

        # --- \u6807\u9898 ---
        w('<h1>\U0001F4DA Kindle \u4f20\u4e66</h1>'.encode())

        # --- \u63d0\u793a\u6d88\u606f ---
        if ok_msg:
            w('<div class="msg msg-ok">{}</div>'.format(html.escape(ok_msg)).encode())
        if err_msg:
            w('<div class="msg msg-err">{}</div>'.format(html.escape(err_msg)).encode())

        # --- IP \u5730\u5740\u5361 ---
        w(b'<div class="ip-box">')
        w('<div class="addr">http://{}:{}</div>'.format(ip, PORT).encode())
        w('<div class="hint">\U0001F4F1 \u624b\u673a / \U0001F4DA Kindle \u6d4f\u89c8\u5668\u6253\u5f00\u6b64\u5730\u5740</div>'.encode())
        w(b'</div>')

        # --- \u4e0a\u4f20\u5361\u7247 ---
        w(b'<div class="card">')
        w('<div class="card-title">\U0001F4E4 \u4e0a\u4f20\u7535\u5b50\u4e66</div>'.encode())
        w(b'<form action="/" method="post" enctype="multipart/form-data">')
        w(b'<input type="file" name="file" multiple>')
        w('<button type="submit">\U0001F4E4 \u4e0a\u4f20</button>'.encode())
        w(b'</form>')
        w(b'</div>')

        # --- \u6587\u4ef6\u5217\u8868\u5361\u7247 ---
        w(b'<div class="card">')
        w('<div class="card-title">\U0001F4DA \u7535\u5b50\u4e66 ({} \u672c)</div>'.format(len(files)).encode())

        if files:
            w(b'<table>')
            w('<tr><th></th><th>\u6587\u4ef6\u540d</th><th></th></tr>'.encode())
            for fname in files:
                fpath = os.path.join(BOOKS_DIR, fname)
                size = fmt_size(os.path.getsize(fpath))
                encoded = urllib.parse.quote(fname)
                icon = file_icon(fname)

                w('<tr>'.encode())
                w('{}'.format(icon).encode())
                w('<td><a class="fname" href="/books/{}" download>{}</a> <span class="size">{}</span></td>'.format(
                    encoded, html.escape(fname), size).encode())
                w('<td><a class="btn-del" href="/?action=delete&file={}">{}</a></td>'.format(
                    encoded, '\u2716').encode())
                w(b'</tr>')
            w(b'</table>')
        else:
            w('<div class="empty">\u6682\u65e0\u7535\u5b50\u4e66<br>\u4e0a\u4f20\u4f60\u7684\u7b2c\u4e00\u672c\u5427 \U0001F4D6</div>'.encode())

        w(b'</div>')
        w(HTML_FOOT.encode('utf-8'))

    def log_message(self, fmt, *args):
        """\u589e\u5f3a\u65e5\u5fd7\u8f93\u51fa\u3002\u652f\u6301\u53ef\u53d8\u53c2\u6570\u3002"""
        timestamp = self.log_date_time_string()
        if len(args) == 3:
            print('[{}] {} {} {}'.format(timestamp, args[0], args[1], args[2]))
        elif len(args) == 2:
            print('[{}] {} {}'.format(timestamp, args[0], args[1]))
        else:
            print('[{}] {}'.format(timestamp, fmt % args if args else fmt))


# ============================================================
# \u5165\u53e3
# ============================================================

def main():
    ip = local_ip()
    book_count = len(os.listdir(BOOKS_DIR))

    print()
    print('  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557')
    print('  \u2551    \U0001F4DA  Kindle WiFi \u4f20\u4e66\u670d\u52a1\u5668        \u2551')
    print('  \u2551                                          \u2551')
    print('  \u2551    \U0001F4F1  \u5728\u540c\u4e00 WiFi \u4e0b\u6253\u5f00:                \u2551')
    print('  \u2551                                          \u2551')
    print('  \u2551    \u2192  http://{}:{}                  \u2551'.format(ip, PORT))
    print('  \u2551                                          \u2551')
    print('  \u2551    \U0001F4C2  \u4e66\u7c4d\u76ee\u5f55:  \u2551')
    print('  \u2551    {}  \u2551'.format(BOOKS_DIR))
    print('  \u2551                                          \u2551')
    print('  \u2551    \U0001F4DA  \u73b0\u6709\u4e66\u7c4d: {} \u672c                    \u2551'.format(book_count))
    print('  \u2551                                          \u2551')
    print('  \u2551    \u2328\uFE0F  Ctrl+C \u505c\u6b62\u670d\u52a1\u5668              \u2551')
    print('  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d')
    print()

    server = http.server.HTTPServer(('0.0.0.0', PORT), KindleTransferHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\u670d\u52a1\u5668\u5df2\u505c\u6b62\u3002')
        server.server_close()


if __name__ == '__main__':
    main()
