from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
os.chdir(Path(__file__).resolve().parent)
print("页面已启动：http://localhost:8013", flush=True)
print("按 Ctrl+C 停止服务", flush=True)
ThreadingHTTPServer(("127.0.0.1", 8013), SimpleHTTPRequestHandler).serve_forever()
