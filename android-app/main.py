#!/usr/bin/env python3
"""Kindle WiFi Transfer - Android App"""
import os, sys, socket, html, mimetypes, shutil, urllib.parse, http.server, threading, time, json, re

PORT = 8080

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except:
        return '127.0.0.1'

BOOKS_DIR = ''
SERVER = None

def make_handler():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            p = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(p.query)
            if p.path == '/api/files':
                try:
                    items = [{'name': e.name, 'size': e.stat().st_size} for e in os.scandir(BOOKS_DIR) if e.is_file()]
                except: items = []
                self.send_json(items); return
            if p.path == '/api/delete':
                f = q.get('file', [None])[0]
                if f:
                    fp = os.path.join(BOOKS_DIR, os.path.basename(f))
                    if os.path.isfile(fp): os.remove(fp)
                self.send_json({'ok': True}); return
            if p.path.startswith('/books/'):
                f = os.path.basename(p.path)
                fp = os.path.join(BOOKS_DIR, f)
                if os.path.isfile(fp):
                    mt, _ = mimetypes.guess_type(f)
                    self.send_response(200)
                    self.send_header('Content-Type', mt or 'application/octet-stream')
                    self.send_header('Content-Disposition', 'attachment; filename="%s"' % f)
                    self.send_header('Content-Length', str(os.path.getsize(fp)))
                    self.end_headers()
                    with open(fp, 'rb') as fh: shutil.copyfileobj(fh, self.wfile)
                    return
            self.send_error(404)
        def do_POST(self):
            if self.path == '/api/upload':
                ct = self.headers.get('Content-Type', '')
                cl = self.headers.get('Content-Length', '0')
                body = self.rfile.read(int(cl))
                boundary = ct.split('boundary=')[-1].strip() if 'multipart' in ct else ''
                names = []
                for part in body.split(b'--' + boundary.encode()):
                    idx = part.find(b'\r\n\r\n')
                    if idx < 0: continue
                    hdr = part[:idx].decode(errors='replace')
                    data = part[idx+4:]
                    m = re.search(r'filename="([^"]*)"', hdr)
                    if m:
                        fn = os.path.basename(m.group(1))
                        fp = os.path.join(BOOKS_DIR, fn)
                        with open(fp, 'wb') as fh: fh.write(data.rstrip(b'\r\n'))
                        names.append(fn)
                self.send_json({'ok': True, 'count': len(names)})
                return
            self.send_error(404)
        def send_json(self, data):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        def log_message(self, *a): pass
    return H

class KindleApp(App):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.server_thread = None
        self.httpd = None
        self.running = False
    def build(self):
        self.title = 'Kindle\u4f20\u4e66'
        Window.clearcolor = (0.96, 0.96, 0.96, 1)
        global BOOKS_DIR
        BOOKS_DIR = os.path.join(self.user_data_dir, 'books')
        os.makedirs(BOOKS_DIR, exist_ok=True)
        ip = local_ip()
        root = BoxLayout(orientation='vertical', spacing=12, padding=16)
        title = Label(text='Kindle \u4f20\u4e66', size_hint=(1,None), height=48, font_size=22, bold=True)
        root.add_widget(title)
        addr = Label(text='http://%s:%d' % (ip, PORT), size_hint=(1,None), height=36,
            font_size=18, bold=True, color=(0.18,0.49,0.2,1))
        root.add_widget(addr)
        self.btn = Button(text='\u25b6 \u542f\u52a8\u670d\u52a1\u5668', size_hint=(0.7,None), height=46,
            pos_hint={'center_x':0.5}, font_size=16,
            background_color=(0.75,0.22,0.17,1), color=(1,1,1,1))
        self.btn.bind(on_press=self.toggle)
        root.add_widget(self.btn)
        hint = Label(text='Kindle \u6d4f\u89c8\u5668\u6253\u5f00\u4e0a\u65b9\u5730\u5740', size_hint=(1,None), height=24, font_size=12)
        root.add_widget(hint)
        Clock.schedule_interval(self.refresh, 3)
        return root
    def toggle(self, btn):
        if self.running: self.stop_server()
        else: self.start_server()
    def start_server(self):
        def task():
            global SERVER
            try:
                SERVER = http.server.HTTPServer(('0.0.0.0', PORT), make_handler())
                SERVER.serve_forever()
            except: pass
        self.server_thread = threading.Thread(target=task, daemon=True)
        self.server_thread.start()
        self.running = True
        self.btn.text = '\u25a0 \u505c\u6b62\u670d\u52a1\u5668'
    def stop_server(self):
        global SERVER
        if SERVER: SERVER.shutdown(); SERVER.server_close(); SERVER = None
        self.running = False
        self.btn.text = '\u25b6 \u542f\u52a8\u670d\u52a1\u5668'
    def refresh(self, dt): pass

if __name__ == '__main__':
    KindleApp().run()
