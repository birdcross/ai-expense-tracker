# 씀로그 Firestore 설계

- 프로젝트: `sseumlog`
- 데이터베이스: `(default)`, Standard, 서울 `asia-northeast3`
- 개인용 단일 저장소. 모든 지출과 상담은 같은 사용자에게 속합니다.
- Python Firebase Admin SDK로 접근합니다. 웹 앱 Firebase API 키는 서버 인증에 사용하지 않습니다.
- 문서 ID는 서버에서 생성하는 UUID 32자리 문자열입니다. API 응답에는 문서 ID를 `id`로 붙입니다.
- Firestore는 컬렉션을 미리 만드는 SQL 테이블 방식이 아닙니다. 첫 문서를 저장하면 해당 컬렉션이 생깁니다.

## `data/{entry_id}` — 지출 항목

| 필드 | Firestore 타입 | 용도 |
|---|---|---|
| date | string | 지출일 `YYYY-MM-DD` |
| value | integer | 원화 금액, 0~1,000,000,000 |
| name | string | 품목명, 1~100자 |
| category | string | 식비, 카페·간식, 생활용품, 의류·신발, 교통, 문화·여가, 건강, 기타 |
| merchant | string | 가게명, 없으면 빈 문자열 |
| memo | string | 메모, 최대 500자 |
| source | string | `manual`, `receipt`, `product`, `sample` |
| receipt_id | string 또는 null | 같은 영수증의 품목을 묶는 ID |
| created_at | string | UTC ISO 8601 생성 시각 |
| updated_at | string, 선택 | 수정 시각, UTC ISO 8601 |

구매 품목 하나가 문서 하나입니다. 영수증 총액은 별도 지출로 저장하지 않아 이중 합산을 막습니다.
영수증 품목 최대 100개는 같은 batch에서 저장합니다. 기존 로컬 파일과 필드 타입을 동일하게 유지합니다.

## `conversations/{conversation_id}` — 소비 상담

| 필드 | Firestore 타입 | 용도 |
|---|---|---|
| title | string | 대화 제목, 최대 100자 |
| messages | array of map | 시간 순서대로 저장한 대화, 최대 100개 |
| messages[].role | string | `user` 또는 `assistant` |
| messages[].content | string | 메시지 본문, 최대 6,000자 |
| updated_at | string | UTC ISO 8601 최종 갱신 시각 |

현재 대화 길이 제한에서는 한 문서의 messages 배열로 충분합니다.
목록 API는 messages를 응답에서 제외하고, 개별 조회에서 전체 대화를 반환합니다.

## 접근 규칙과 인덱스

`firestore.rules`는 클라이언트 직접 읽기·쓰기를 모두 거부합니다. Admin SDK는 서버의 서비스 계정 권한으로 접근합니다.
API 접근 제어는 `APP_ACCESS_TOKEN`으로 수행합니다. 외부 공개 전 접근 암호를 반드시 설정합니다.

현재 API는 전체 문서를 읽어 Python에서 필터·정렬·통계를 계산하므로 복합 인덱스가 필요하지 않습니다.
`firestore.indexes.json`은 검색하지 않는 메모와 messages의 자동 인덱싱을 제외하는 설정입니다.
이 파일은 저장된 배포 설정이며, 콘솔에 자동 반영되지는 않습니다.

## 연결 및 확인

서비스 계정 JSON은 `backend/service-account.json`에 저장하고 `.env`에 아래 값을 설정합니다.
키 파일은 Git에서 제외됩니다. 개인 키 내용은 프론트나 문서에 넣지 않습니다.

```dotenv
STORAGE_MODE=firestore
FIREBASE_PROJECT_ID=sseumlog
GOOGLE_APPLICATION_CREDENTIALS=D:/python/sseumlog/backend/service-account.json
```

`FIREBASE_SERVICE_ACCOUNT_JSON`에 내용이 있다면 파일 경로보다 우선하므로 두 방식 중 하나만 사용합니다.
연결 후 `python backend/check_firestore.py`로 지출·대화의 쓰기와 읽기를 검사합니다.
검사 문서는 전용 `_connection_checks` 컬렉션에 남기며 실제 지출 통계와 대화에 섞이지 않습니다.
기존 로컬 가상 데이터는 자동으로 Firestore에 복사하지 않습니다.

다중 사용자 앱으로 확장할 때는 Firebase Authentication과 `users/{uid}/entries`,
`users/{uid}/conversations` 구조로 옮겨 사용자별 권한을 분리해야 합니다.
