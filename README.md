# MoTix Printer Controller

MoEco 핸드헬드 잉크젯 프린터를 웹 브라우저에서 제어하는 단일 페이지 애플리케이션입니다.

---

## 파일 구조

| 파일 | 역할 |
|------|------|
| `printer_ui.html` | UI 구조 (DOM) |
| `printer_ui.css` | 스타일 |
| `printer_ui.js` | 전체 로직 (상태 관리, API 통신, 이벤트) |
| `bridge.py` | CORS 프록시 서버 (브라우저 ↔ 프린터 중계) |
| `FindEndpoint.py` | 프린터 API 엔드포인트 탐색 유틸리티 |
| `StartEngine.py` | 프린터 엔진 API 집중 탐색 유틸리티 |

---

## 네트워크 구조

```
브라우저 (printer_ui.html)
    ↓ HTTP
bridge.py (localhost:8765)
    ├─ /engine/* → 172.30.1.15:9966  (엔진 API)
    └─ /data/*   → 172.30.1.15:9911  (데이터 API)
```

- **port 9966** — 인쇄 엔진 제어 (`/engine/real`, `/engine/printjob`, `/engine/dynamic`)
- **port 9911** — 데이터 파일 관리 (`/data/messages`, `/data/list` 등)
- `bridge.py`는 브라우저의 CORS 제약을 우회하기 위한 로컬 프록시

---

## 실행 방법

### 1. bridge.py 시작

프린터 IP를 인자로 전달하여 실행합니다.

```bash
python bridge.py <프린터_IP>
```

예시:
```bash
python bridge.py 172.30.1.15
```

IP를 입력하지 않으면 실행이 중단됩니다:
```
Usage: python bridge.py <printer_ip>
```

출력 확인:
```
Proxy running: http://localhost:8765
  /engine/* → http://<프린터_IP>:9966
  /data/*   → http://<프린터_IP>:9911
```

### 2. 브라우저에서 열기

`printer_ui.html` 파일을 더블클릭해서 바로 열면 됩니다.

> 이 앱은 HTTP fetch를 사용하므로 로컬 서버 없이도 동작합니다.  
> `bridge.py`가 CORS 헤더를 처리하기 때문에 `file://` 프로토콜로 열어도 정상 작동합니다.

---

## UI 기능

### Printer Status 카드
- 프린터 연결 상태 표시 (Connected / Disconnected)
- 현재 엔진 상태 표시: `state` · `message` · `output`
- 현재 메시지의 필드 목록을 태그로 표시 (`id · name`)
- **Refresh** 버튼: 프린터 상태 수동 재조회 (최초 연결 성공 시 활성화)
- 페이지 로드 시 자동으로 1회 상태 조회 실행

### Message 카드
- Refresh(또는 페이지 로드) 시 프린터에 로드된 메시지명이 자동으로 입력창에 반영
- 직접 타이핑으로 다른 메시지명 입력 가능
- 이전에 사용한 메시지명을 자동완성으로 제안 (localStorage 저장, 최대 20개)
- 모든 Send / Generator 카드는 이 카드에서 설정한 메시지를 사용

### Send 카드
- 입력 필드를 동적으로 추가/제거할 수 있는 통합 전송 카드
- 페이지 로드 시 필드 1개로 시작
- **+ 필드 추가** 버튼 클릭 시 필드 행 추가
- 각 행의 **−** 버튼으로 해당 필드 제거 (1개만 남으면 − 버튼 숨김)
- 필드 라벨은 현재 메시지의 `source_info` 순서대로 자동 표시
- **Send** 클릭 시 모든 필드 값을 순서대로 전송
- Message 카드 미입력 시 `Msg2` 사용

### Sequence Generator 카드
- **Count**: 생성할 버튼 개수 입력
- **두 번째 필드 값**: 모든 버튼에 공통으로 들어갈 값 입력
- **Generate** 클릭 시 `1 {값}` · `2 {값}` · ... · `N {값}` 형태의 버튼 N개 생성
- 버튼 클릭 시 즉시 사라지며 2개 필드로 전송
  - `source_info[0]` ← 순번 (1, 2, 3...)
  - `source_info[1]` ← 공통 값
- Generate 재클릭 시 기존 버튼 초기화 후 새로 생성
- Message 카드 미입력 시 `Msg1` 사용

### Button Generator 카드
- 값을 입력하고 **Generate** 클릭 (또는 Enter) 시 해당 값이 적힌 버튼 생성
- 여러 개 미리 만들어두고 순서대로 클릭 가능
- 버튼 클릭 시 즉시 사라지며 첫 번째 필드(`source_info[0]`)에 값을 넣어 전송
- Message 카드 미입력 시 `Msg2` 사용

### Log 카드
- 모든 API 요청/응답을 타임스탬프와 함께 색상 구분 기록
  - 파란색: 일반 정보
  - 초록색: 성공
  - 빨간색: 오류
- **Clear** 버튼으로 로그 초기화

---

## 인쇄 시퀀스 (`printSequence`)

모든 Send / Generator 버튼은 동일한 `printSequence(msgName, values)` 함수를 사용합니다.  
`values`는 전송할 값의 배열이며, 필드명은 함수 내부에서 `currentFields` 기준으로 자동 결정됩니다.

```
1. GET /engine/real  →  현재 상태 확인
   │
   ├─ [같은 메시지 + started 상태]
   │      재시작 생략, 바로 3번으로 (프린터 화면 전환 없음)
   │
   └─ [다른 메시지 또는 completed 상태]
          DELETE /engine/printjob   현재 작업 정지
                   ↓ 500ms
          POST   /engine/printjob   새 메시지 로드
                   ↓ 1000ms
          GET    /engine/real       새 메시지의 source_info 갱신 → currentFields 업데이트
                   ↓
2. values 배열 → currentFields 기준으로 data 배열 구성
3. POST /engine/dynamic  →  데이터 전송 (인쇄 실행)
```

### 필드 매핑

`values[n]`은 `source_info[n].name` 필드에 자동 매핑됩니다.  
메시지 전환 시 `currentFields`가 새 메시지 기준으로 갱신되므로, 필드명이 달라도 정상 동작합니다.

| values 인덱스 | 매핑 필드명 |
|---|---|
| `values[0]` | `source_info[0].name` |
| `values[1]` | `source_info[1].name` |
| `values[n]` | `source_info[n].name` |

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/engine/real` | 현재 엔진 상태, 로드된 메시지명, 필드 정보(`source_info`) 조회 |
| `GET` | `/engine/status` | 라인별 인쇄 상태 조회 |
| `DELETE` | `/engine/printjob` | 현재 인쇄 작업 정지 |
| `POST` | `/engine/printjob` | 인쇄 작업 시작 (메시지 로드) |
| `POST` | `/engine/dynamic` | 동적 데이터 전송 (인쇄 실행) |

### POST /engine/printjob 요청 예시
```json
{
  "hash": 11112,
  "attribute": { "print_data_name": "Msg1" }
}
```

### POST /engine/dynamic 요청 예시
```json
{
  "print_mode": "single",
  "data": [
    { "type": "text", "name": "Dyn.Text",  "content": "1" },
    { "type": "text", "name": "Dyn.Text1", "content": "2000" }
  ]
}
```

---

## 참고 사항

- 프린터 메시지 템플릿(Msg1, Msg2 등)은 펌웨어 내장 템플릿으로 API를 통한 목록 조회가 불가능합니다. 메시지명은 프린터 설정 소프트웨어(MoEco PrintStation 등)에서 확인하세요.
- Message 카드에서 메시지명을 직접 변경한 경우 **Refresh를 눌러야** `currentFields`가 새 메시지 기준으로 갱신됩니다.
- `bridge.py`가 실행 중이어야 UI가 동작합니다.
- 브라우저는 Chrome / Edge 권장입니다.
