"""
MoEco 프린터 API 엔드포인트 탐색 스크립트
- 포트 스캔 후 열린 포트에서 엔드포인트 탐색
- 알려진 패턴 기반으로 GET/POST 요청을 시도
"""

import socket
import requests
import json
from itertools import product

PRINTER_IP = "172.30.1.15"
# 탐색할 포트 목록 (알려진 포트 + 주변 범위)
SCAN_PORTS = [
    9911, 9966, 8765, 8080, 8000, 80,
    9900, 9901, 9910, 9912, 9920, 9960, 9970,
    10000, 10080, 3000, 5000,
]
BASE = f"http://{PRINTER_IP}:9911"  # 포트 스캔 후 자동 교체됨
TIMEOUT = 2

# 알려진 경로 세그먼트 조합
PREFIXES = ["", "/engine", "/data", "/api", "/print", "/job", "/device", "/status"]
SEGMENTS = [
    "messages", "message", "list", "all",
    "printjob", "jobs", "real", "dynamic",
    "template", "templates", "msg", "info",
    "config", "settings", "files", "data",
]
METHODS = ["GET", "POST"]

# 직접 시도할 완전한 경로 목록 (우선순위 높음)
PRIORITY_PATHS = [
    "/engine/messages",
    "/engine/message",
    "/engine/list",
    "/engine/all",
    "/engine/template",
    "/engine/templates",
    "/data/list",
    "/data/messages",
    "/data/all",
    "/data/files",
    "/print/list",
    "/print/messages",
    "/api/messages",
    "/api/list",
    "/messages",
    "/templates",
    "/jobs",
]

HEADERS = {"Content-Type": "application/json"}

def try_request(method, path):
    url = f"{BASE}{path}"
    try:
        resp = requests.request(method, url, headers=HEADERS, timeout=TIMEOUT)
        return resp.status_code, resp.text[:300]
    except requests.exceptions.ConnectionError:
        return None, "Connection refused"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def print_result(method, path, status, body):
    status_str = str(status) if status else "---"
    # 200~299는 성공으로 강조
    tag = "✅" if status and 200 <= status < 300 else ("⚠️ " if status and status < 500 else "  ")
    print(f"{tag} [{status_str}] {method:6} {path}")
    if status and 200 <= status < 300:
        try:
            parsed = json.loads(body)
            print(f"       → {json.dumps(parsed, ensure_ascii=False, indent=2)[:400]}")
        except Exception:
            print(f"       → {body[:200]}")

def scan_ports():
    """열린 포트를 찾아 반환"""
    print(f"🔎 포트 스캔 중: {PRINTER_IP}")
    open_ports = []
    for port in SCAN_PORTS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((PRINTER_IP, port))
            s.close()
            if result == 0:
                print(f"  ✅ 포트 {port} 열림")
                open_ports.append(port)
            else:
                print(f"  ✗  포트 {port} 닫힘")
        except Exception as e:
            print(f"  ✗  포트 {port} 오류: {e}")
    return open_ports

def probe_root():
    """루트 경로 응답으로 서버 힌트 파악"""
    print("\n[루트 탐색] GET / 응답 확인...")
    url = f"{BASE}/"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        print(f"  상태: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type', '없음')}")
        print(f"  Server: {resp.headers.get('Server', '없음')}")
        print(f"  응답 본문 (첫 500자):\n{'-'*40}\n{resp.text[:500]}\n{'-'*40}")
    except Exception as e:
        print(f"  오류: {e}")

def scan_port_endpoints(port):
    """특정 포트에서 엔드포인트 탐색"""
    global BASE
    BASE = f"http://{PRINTER_IP}:{port}"
    print(f"\n{'='*60}")
    print(f"[포트 {port}] 탐색 시작: {BASE}")

    probe_root()

    found = []

    print(f"\n  [1단계] 우선순위 경로...")
    for path in PRIORITY_PATHS:
        for method in METHODS:
            status, body = try_request(method, path)
            print_result(method, path, status, body)
            if status and 200 <= status < 300:
                found.append((method, path, status, body))

    print(f"\n  [2단계] 조합 경로...")
    for prefix, seg in product(PREFIXES, SEGMENTS):
        path = f"{prefix}/{seg}"
        if path in PRIORITY_PATHS:
            continue
        status, body = try_request("GET", path)
        if status:
            print_result("GET", path, status, body)
            if 200 <= status < 300:
                found.append(("GET", path, status, body))

    return found

def main():
    global BASE

    # 0단계: 포트 스캔
    print("=" * 60)
    open_ports = scan_ports()
    if not open_ports:
        print(f"\n❌ {PRINTER_IP} 에서 열린 포트를 찾을 수 없습니다.")
        print("   프린터 전원 및 네트워크 연결을 확인하세요.")
        return

    print(f"\n열린 포트: {open_ports}")

    # 열린 포트 전체 탐색
    all_found = {}
    for port in open_ports:
        found = scan_port_endpoints(port)
        if found:
            all_found[port] = found

    # 전체 결과 요약
    print(f"\n{'='*60}")
    print(f"\n📋 전체 성공 응답 요약:\n")
    if all_found:
        for port, results in all_found.items():
            print(f"  [포트 {port}]")
            for method, path, status, body in results:
                print(f"    {method} {path}  [{status}]")
                try:
                    keys = list(json.loads(body).keys())
                    print(f"      응답 키: {keys}")
                except Exception:
                    pass
    else:
        print("  성공 응답 없음")

if __name__ == "__main__":
    main()