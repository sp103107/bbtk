#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, socket, sys
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'repo_scaffold'/'app'

def load_server():
    spec=importlib.util.spec_from_file_location('bbtc_server', APP/'server.py')
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def local_ips():
    ips=set()
    try:
        host=socket.gethostname()
        for item in socket.getaddrinfo(host, None):
            ip=item[4][0]
            if '.' in ip and not ip.startswith('127.'):
                ips.add(ip)
    except Exception:
        pass
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        ip=s.getsockname()[0]
        if not ip.startswith('127.'):
            ips.add(ip)
        s.close()
    except Exception:
        pass
    return sorted(ips)

def main():
    ap=argparse.ArgumentParser(description='Start Best Buds Time Clock for phone/tablet kiosk use on the local network.')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8080)
    args=ap.parse_args()
    mod=load_server(); mod.init_db()
    websocket_state=mod.start_live_websocket_server(args.host, args.port + 1)
    print('Best Buds Time Clock local-network kiosk launcher', flush=True)
    print(f'Listening on http://{args.host}:{args.port}', flush=True)
    if websocket_state['available']:
        print(f'Owner live WebSocket on ws://{args.host}:{args.port + 1}', flush=True)
    else:
        print(f"Owner live WebSocket unavailable; polling fallback active: {websocket_state['error']}", flush=True)
    ips=local_ips()
    if ips:
        print('Open one of these from the phone/tablet on the same Wi-Fi:', flush=True)
        for ip in ips:
            print(f'  http://{ip}:{args.port}', flush=True)
            print(f'  health: http://{ip}:{args.port}/api/health', flush=True)
    else:
        print('Could not detect LAN IP automatically. Run ipconfig/ifconfig and open http://YOUR-IP:%s' % args.port, flush=True)
    print('Do not open repo_scaffold/app/static/index.html directly for live punches.', flush=True)
    ThreadingHTTPServer((args.host, args.port), mod.Handler).serve_forever()
if __name__=='__main__': main()
