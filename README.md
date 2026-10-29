# 씀로그 — 사진으로 기록하고 AI로 이해하는 소비

영수증 또는 상품 사진에서 구매 항목과 금액을 추출하고, 확인한 지출을 저장해 소비 패턴을 분석하는 개인용 웹 앱입니다. 카드사 연결은 하지 않습니다.

## 현재 실행 상태

- 로컬 앱: http://127.0.0.1:8017
- 로컬 Swagger: http://127.0.0.1:8017/docs
- Vercel 앱·API URL: https://ai-expense-tracker-tau-sepia.vercel.app
- 배포 Swagger: https://ai-expense-tracker-tau-sepia.vercel.app/docs
- Render: 사용하지 않음. 현재 Vercel에서 화면과 FastAPI를 함께 실행합니다.
- 기본값은 **시연 모드**입니다. 로컬 JSON에 영구 저장하고 채팅은 통계 기반 시연 문구를 반환합니다. 사진 인식은 실제처럼 흉내 내지 않고 비활성화합니다.
- 현재 로컬 설정: 실제 OpenAI 호환 상담(`gpt-5-mini`), Anthropic 사진 분석(`claude-haiku-4`), Firestore 프로젝트 `sseumlog` 연결. 상담 응답, Firestore 쓰기·읽기, 가상 영수증과 상품 이미지 분석을 실검증했습니다. 프롬프트 수정 후 가상 영수증 2개 항목 12,200원과 가격 없는 상품의 금액 null 처리를 확인했습니다. 실제 촬영 사진의 정확도는 추가 확인이 필요합니다.
- 120일 가상 지출 + 화면 저장 검증용 가상 지출 1건을 로컬에 준비했습니다. 실제 소비 기록이 아닙니다. 이 로컬 파일은 Git에서 제외됩니다.

## 주요 기능

1. **영수증 등록**: 상품명·카테고리·항목별 금액·날짜·가게명 추출 → 수정 → 일괄 저장. 항목 금액은 수량이 반영된 줄 전체 금액입니다. 최종 결제 총액은 검증용으로만 사용하므로 이중 합산하지 않습니다.
2. **상품 사진 등록**: 상품 하나의 이름과 분류 인식. 명확한 가격표가 있으면 가격도 추출하고, 없거나 여러 가격이 모호하면 사용자가 입력합니다.
3. **직접 입력 및 CRUD**: 날짜·금액·항목·메모·가게·카테고리 수정 및 삭제. 검색과 분류 필터.
4. **소비 대시보드**: 기간·개수·합계·건당 평균·최대·최소·일평균·카테고리별 합계·최근 추세·30일 그래프.
5. **AI 상담**: 저장된 지출 요약을 시스템 프롬프트에 주입. 대화 자동 저장, 목록 조회, 개별 대화 불러오기 및 이어가기, 삭제.
6. CSV 내보내기, 다크 모드, 모바일 화면, 로딩·실패 안내.

영수증 합계와 항목 합계가 다르면 저장 전 항목 금액을 수정해야 합니다. 할인은 실제 결제액에 맞춰 각 항목에 반영해주세요. 흐릿한 영수증·한글 약칭·복수 상품 사진의 인식은 틀릴 수 있으므로 결과를 반드시 확인합니다. 같은 구매를 재업로드하면 중복될 수 있으며 자동 중복 제거는 구현하지 않았습니다.

## 기술 스택과 구조

- 백엔드: Python 3.10+, FastAPI, Pydantic, Uvicorn
- DB: 로컬 JSON 기본 / 선택적으로 Firestore (STORAGE_MODE=firestore)
- AI: OpenAI 호환 텍스트 상담 / Anthropic 또는 OpenAI 호환 이미지 분석
- 프론트: HTML/CSS/바닐라 JavaScript, SVG 그래프 (프레임워크 없음)
- 배포 설정: Render `render.yaml`, Vercel `frontend/vercel.json`

```text
backend/
  main.py             # uvicorn 진입점
  app/main.py         # 앱, CORS, 로컬 프론트 제공
  app/routers.py      # API 경로, 인증, 요청 흐름
  app/models.py       # 요청·분석 결과 검증
  app/services.py     # 시계열 통계, 이미지 인식, 컨텍스트 주입
  app/store.py        # Firestore 및 시연 저장소
  tests/test_app.py   # 핵심 동작 테스트
frontend/
  index.html, style.css, app.js
  build.mjs           # API_BASE_URL을 공개 설정 파일로 생성
docs/screenshots/     # 로컬 시연 화면
```

라우터는 요청·응답을 연결하고, 서비스는 통계 및 AI 작업을, 저장소는 DB 접근을 담당합니다. Pydantic은 유효한 날짜, 0 이상 정수 원화, 금액 상한, 문자열 길이, 분류, 메시지 역할을 검증합니다. AI가 반환한 JSON도 다시 검증합니다.

## 로컬 실행

Windows에서 프로젝트 폴더의 `start.ps1`을 실행합니다. 현재 작업 폴더에는 설치된 `.venv`가 있습니다. 새 환경에서는 Python을 설치한 뒤 다음을 실행합니다.

```powershell
py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
New-Item backend/.env -ItemType File
Set-Location backend
../.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8017
```

브라우저에서 http://127.0.0.1:8017 을 엽니다. 빈 저장소에서는 연결 설정(톱니바퀴)의 **시연 데이터 120건 만들기**를 누릅니다. 가상 데이터는 120일에 걸쳐 하루 한 건씩 생성되며, 실제 결제 내역이 아닙니다. 시연 저장은 단일 프로세스용이므로 여러 worker로 실행하지 않습니다.

## 실제 AI·Firestore 연결

1. Firebase 프로젝트에서 Firestore Database를 생성합니다.
2. 서비스 계정 키를 생성하고 `backend/.env`의 `FIREBASE_SERVICE_ACCOUNT_JSON`에 JSON을 한 줄 문자열로 입력합니다. 파일을 쓴다면 `GOOGLE_APPLICATION_CREDENTIALS`에 절대 경로를 지정합니다.
3. `OPENAI_API_KEY`, `APP_ACCESS_TOKEN`을 설정하고 `APP_MODE=production`으로 바꿉니다.
4. 서버를 재시작하고 화면의 연결 설정에 **앱 접근 암호**를 입력합니다. OpenAI 키를 브라우저에 입력하지 않습니다.
5. 영수증 1장과 상품 사진 1장으로 분석·수정·저장을 확인합니다. 이어서 AI 채팅과 `/docs`를 확인합니다.

사진 원본은 파일 저장소나 Firestore에 저장하지 않습니다. 분석할 때만 OpenAI로 전송하고, 확정한 텍스트·금액을 저장합니다. 영수증에 카드번호 등 민감정보가 있다면 먼저 가리세요.

| 환경 변수 | 용도 |
|---|---|
| `APP_MODE` | `demo` 또는 `production` |
| `OPENAI_API_KEY` | 백엔드 전용 AI 키 |
| `OPENAI_MODEL` | 이미지 입력 지원 모델, 기본 `gpt-4.1-mini` |
| `VISION_PROVIDER` | `openai` (기본) 또는 `anthropic`, 사진 분석 경로 선택 |
| `VISION_MODEL` | 사진 분석 모델. 현재 `claude-haiku-4` |
| `ANTHROPIC_BASE_URL` | Anthropic 호환 API 서버 주소. 현재 `https://copa.codyssey.kr` |
| `ANTHROPIC_API_KEY` | 사진 분석 전용 Anthropic 호환 키. OpenAI 키와 별도 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firestore 서비스 계정 JSON |
| `GOOGLE_APPLICATION_CREDENTIALS` | JSON 대신 사용하는 서비스 계정 파일 경로 |
| `APP_ACCESS_TOKEN` | 개인 앱 API 접근 암호, 운영 모드 필수 |
| `ALLOWED_ORIGINS` | 프론트 주소를 쉼표로 나열, 끝 `/` 제외 |
| `API_BASE_URL` | Vercel 빌드 시 사용할 Render API 원점 주소 |
| `LOCAL_DATA_PATH` | 선택: 시연 JSON 경로 |

개인용 단일 저장소 앱입니다. 접근 암호를 아는 사용자는 동일한 기록을 봅니다. 다중 사용자 서비스로 확장하려면 Firebase Authentication 및 사용자별 데이터 격리가 필요합니다. Firestore는 백엔드 서비스 계정으로만 접근하므로 브라우저 직접 읽기·쓰기는 허용하지 않아도 됩니다. CORS는 브라우저의 교차 출처 요청 제한이며 인증을 대신하지 않습니다.

## 데이터 구조와 통계 기준

`data/{id}`:

```json
{
  "date": "2026-10-28", "value": 89000,
  "name": "운동화", "category": "의류·신발",
  "memo": "가격 확인 완료", "merchant": "신발 가게",
  "source": "product", "receipt_id": null,
  "created_at": "2026-10-28T06:00:00+00:00"
}
```

`conversations/{id}`: `title`, `messages: [{role, content}]`, `updated_at`.

- 지출 데이터 포인트는 구매 항목 한 건입니다. 같은 날짜의 여러 항목은 일별 그래프에서 합산합니다.
- `average`: 건당 평균. `daily_average`: 첫 기록부터 마지막 기록까지의 달력 일수로 나눈 일평균.
- 무기록일은 0원으로 계산합니다. 따라서 기록 누락은 통계에 영향을 줍니다.
- 추세는 한국 시간 오늘 기준 최근 7일과 직전 7일 합계 비교. 이전 합계가 0이면 증가율은 null입니다.
- `this_month`는 이번 달 오늘까지, `last_month`는 지난달 전체입니다. AI 프롬프트에서 기간 차이를 설명하도록 합니다.
- 채팅은 `GET /api/data/summary`와 동일한 서비스 함수로 최신 요약을 만들고 시스템 프롬프트에 삽입합니다. 자기 서버에 HTTP 요청을 보내는 대신 같은 로직을 재사용합니다.
- AI에는 최근 대화 최대 20개와 통계 요약이 전달되며 개별 구매 내역 전체는 전달되지 않습니다. 특정 상품 상세 질문에는 제한이 있습니다.

```text
사진 → OpenAI 분석 → 결과 검증 → 사용자 확인 → data 저장
질문 → data 조회·요약 → 시스템 프롬프트 + 최근 대화 → GPT 응답
                                               → conversations 자동 저장
```

## API

보호된 API는 `X-App-Token` 헤더를 사용합니다. Swagger의 각 요청에도 입력란이 있습니다.

| Method | 경로 | 기능 |
|---|---|---|
| POST / GET | `/api/data` | 추가 / 전체 목록 |
| PUT / DELETE | `/api/data/{key}` | 수정 / 삭제 |
| POST | `/api/data/batch` | 최대 100개 항목 원자적 저장 |
| GET | `/api/data/summary` | 통계 요약 |
| POST | `/api/analyze` | multipart `file`, `kind=receipt 또는 product` |
| POST | `/api/chat` | `message`, 선택 `conversation_id` |
| POST / GET | `/api/conversations` | 대화 저장 / 목록 |
| GET / DELETE | `/api/conversations/{key}` | 전체 메시지 불러오기 / 삭제 |
| GET | `/api/status` | 저장소·AI 모드 |
| POST | `/api/demo/seed` | 시연 모드·빈 저장소에서만 120건 생성 |
| GET | `/health` | 공개 상태 확인 |

대화 목록에는 `messages`를 포함하지 않습니다. 개별 조회에서 전체 메시지를 반환합니다. 삭제는 즉시 반영되며 앱의 복구 기능은 없습니다.

## Render / Vercel 배포

### 현재 방식: Vercel 한 프로젝트에 전체 앱 배포

저장소 루트(`./`)와 FastAPI 프리셋을 사용합니다. 루트의 `app.py`, `requirements.txt`, `vercel.json`이 배포 진입점과 의존성을 지정합니다. 프론트는 같은 서버에서 제공하므로 `API_BASE_URL` 설정은 필요하지 않습니다.

운영 환경에는 `APP_MODE=production`, `STORAGE_MODE=firestore`, `APP_ACCESS_TOKEN`, OpenAI 상담 설정, Anthropic 사진 분석 설정, `FIREBASE_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_JSON`을 Vercel 서버 전용 비공개 환경변수로 설정합니다. 현재 키는 Production에만 저장되어 있으며 GitHub에는 없습니다. 웹 화면의 연결 설정에는 앱 접근 암호만 입력합니다.

실제 배포에서 비인증 API 차단, 비밀 파일 경로 404, Firestore 읽기·쓰기·수정, 상담 응답, 가상 영수증 12,200원 분석을 확인했습니다. 배포 확인용 지출과 상담 기록은 검사 후 삭제합니다.

### 대안: 프론트 Vercel + 백엔드 Render 분리 배포

1. 이 폴더를 GitHub 저장소에 올립니다. `.env`, 서비스 계정 파일, `.venv`, 시연 JSON을 올리지 않습니다.
2. Render에서 저장소의 `render.yaml`을 Blueprint로 사용하거나 Web Service를 생성합니다. Root Directory `backend`, Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`.
3. Render 환경 변수에 운영 모드, STORAGE_MODE=firestore와 위의 백엔드 비밀값을 설정합니다. `ALLOWED_ORIGINS`는 실제 Vercel 도메인으로 지정합니다.
4. Render의 `/health`와 `/docs`를 확인합니다. 토큰을 넣어 CRUD 및 AI 동작을 검증합니다.
5. Vercel에 같은 저장소를 연결하고 Root Directory를 `frontend`, Framework를 Other로 설정합니다. Build `node build.mjs`, Output `dist`. `API_BASE_URL=https://실제서비스.onrender.com`을 설정한 후 배포합니다.
6. API 주소가 바뀌면 Vercel 재빌드가 필요합니다. 배포 화면 연결 설정의 수동 주소가 있으면 그 주소가 우선합니다. 해당 브라우저에서 실제 서버 주소로 다시 설정하세요.
7. README 상단의 배포 URL을 실제 값으로 채우고, 운영 모드 스크린샷으로 아래 이미지를 교체합니다.

Render 무료 인스턴스가 잠들었으면 첫 요청이 오래 걸릴 수 있습니다. 화면에 안내 문구가 있고 90초 요청 제한 후 재시도를 안내합니다. 시연 모드의 로컬 파일은 Render 재배포 시 보존을 보장하지 않으므로 배포는 Firestore를 쓰는 운영 모드로 진행하세요.

OpenAI 호출은 유료일 수 있습니다. 사진 분석 최대 출력 3,000토큰, 채팅 700토큰, 이미지 8MB, 프로세스당 AI 요청 분당 10회로 제한했습니다. 제공자 대시보드에서도 사용 한도를 설정하세요.

## 검증

```powershell
Set-Location backend
../.venv/Scripts/python.exe -m pytest -q
Set-Location ../frontend
node --check app.js
node build.mjs
```

자동 테스트 12개: CRUD·입력 검증, 일괄 저장 원자성, 요약 합산, 추세 계산, 대화 자동 저장·불러오기·삭제, 시연 데이터, 접근 암호, AI 응답 스키마 및 합계 불일치 처리(모의 응답), 이미지 형식 거부, Swagger 및 정적 파일 제공, 실제 AI 모드의 로컬 저장, 호환 API 주소, Anthropic 이미지 요청·코드 블록 JSON·잘못된 금액 거부.

수동 외부 연동 시험: 실행 중인 서버에 `python backend/tests/manual_vision_check.py`로 가상 영수증·상품 이미지를 전송합니다. 실행 환경에 Pillow가 필요하며 실제 API 사용량이 발생합니다. 테스트 결과는 `docs/vision-smoke/result.json`에 기록하며 지출을 DB에 저장하지 않습니다.

브라우저에서 직접 입력 저장 → 통계 반영 → 상담 전송 → 보관함 → 대화 다시 불러오기를 확인했습니다. Firestore 읽기·쓰기와 가상 이미지 AI 분석도 확인했습니다. 실제 촬영 사진의 인식 정확도와 Render/Vercel 배포는 추가 확인해야 합니다.

## 화면 기록 (로컬 시연)

실제 AI 응답이나 실제 카드 지출을 보여주는 제출 증빙이 아니라 **가상 데이터 기반 로컬 UI 확인용**입니다.

| 화면 | 파일 |
|---|---|
| 대시보드 | [dashboard.png](docs/screenshots/dashboard.png) |
| 지출 관리 | [records.png](docs/screenshots/records.png) |
| 데이터 요약 | [chat.png](docs/screenshots/chat.png) |
| 질문·답변 및 대화 불러오기 결과 | [chat-loaded.png](docs/screenshots/chat-loaded.png) |
| 대화 목록 | [history.png](docs/screenshots/history.png) |

## 로컬 AI 연결 (추가)

ackend/.env에서 APP_MODE=production, STORAGE_MODE=local, OPENAI_API_KEY를 설정하면 Firestore 없이 실제 AI와 로컬 저장을 함께 사용합니다. OpenAI 호환 게이트웨이는 OPENAI_BASE_URL=https://서비스주소/v1과 해당 서비스의 OPENAI_MODEL을 지정합니다. 실제 키는 Git에서 제외되는 backend/.env에만 넣습니다. 로컬 실행은 접근 암호 없이 가능하며, 외부 배포 시 APP_ACCESS_TOKEN을 설정하세요. Firestore 사용 시에는 STORAGE_MODE=firestore와 서비스 계정을 설정합니다.
