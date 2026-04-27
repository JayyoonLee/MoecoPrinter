"""
port 9966 엔진 API 전체 GET 탐색
- 프린터가 인쇄 실행 중인 상태에서 실행하세요
"""

import requests
import json

ENGINE = "http://172.30.1.15:9966"
DATA   = "http://172.30.1.15:9911"
TIMEOUT = 2
HEADERS = {"Content-Type": "application/json"}

GET_PATHS = [
    "/engine/real",
    "/engine/status",
    "/engine/messages",
    "/engine/message",
    "/engine/list",
    "/engine/data",
    "/engine/info",
    "/engine/files",
    "/engine/template",
    "/engine/templates",
    "/engine/printjob",
    "/engine/job",
    "/engine/jobs",
    "/engine/queue",
    "/engine/history",
    "/engine/log",
    "/engine/config",
]

POST_PATHS_WITH_BODIES = [
    ("/data/messages", None),
    ("/data/messages", {}),
    ("/data/messages", {"type": "all"}),
    ("/data/messages", {"action": "list"}),
    ("/data/list",     None),
    ("/data/list",     {}),
    ("/data/list",     {"type": "message"}),
    ("/data/all",      None),
    ("/data/all",      {}),
]

def req(base, method, path, body=None):
    try:
        resp = requests.request(
            method, f"{base}{path}", headers=HEADERS,
            json=body, timeout=TIMEOUT
        )
        return resp.status_code, resp.text[:400]
    except Exception as e:
        return None, str(e)

def show(method, port, path, status, body, extra=""):
    tag = "✅" if status and 200 <= status < 300 else ("⚠️ " if status and status < 500 else "  ")
    print(f"{tag} [{status or '---'}] {method:6} :{port}{path}{extra}")
    if status and 200 <= status < 300:
        try:
            print(f"       → {json.dumps(json.loads(body), ensure_ascii=False)[:400]}")
        except Exception:
            print(f"       → {body[:300]}")

def main():
    print("=" * 60)
    print("프린터 메시지 목록 탐색 (엔진 실행 중 상태에서 실행)\n")

    print("[1] GET :9966/engine/* 탐색")
    for path in GET_PATHS:
        s, b = req(ENGINE, "GET", path)
        if s:
            show("GET", "9966", path, s, b)

    print(f"\n[2] POST :9911/data/* 다양한 body 시도")
    for path, body in POST_PATHS_WITH_BODIES:
        s, b = req(DATA, "POST", path, body)
        if s:
            show("POST", "9911", path, s, b, f"  body={body}")

if __name__ == "__main__":
    main()

