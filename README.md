# Valuverse

다양한 경매 방식 + 재능 거래 + 포인트 예측시장을 결합한 AI 보조 경매 플랫폼.
Notion 기획서·요구사항 명세서·개발명세서 기준으로 구현한다.

| 디렉터리 | 내용 |
|---|---|
| [`backend/`](backend/README.md) | FastAPI + SQLAlchemy. 아래 기능 목록 참고. 테스트 pytest. |
| [`frontend/`](frontend/README.md) | Next.js. **디자인 없이** 백엔드 API 연동만 확인하는 최소 화면 |

## 구현 범위

기본 CRUD(회원/상품/입찰/스킬/예측/포인트/리뷰/신고) 위에 다음 로직을 얹었다.

- **일반 경매**: 실시간 입찰(WebSocket), 마감 임박 자동 연장, 낙찰 확정, 즉시구매, 조기 마감, 동시 입찰 행 잠금
- **블라인드 경매**: 1st-price / Vickrey(2nd-price), 마감 시 일괄 공개, 타입별 입찰 분리
- **스킬 경매**: 예약(낙찰)=포인트 차감·에스크로 보관, 완료 정산, 노쇼 처리, 취소 환불
- **예측시장**: 파리뮤추얼 배당률, 관리자 정산 + 포인트 배당 지급
- **포인트 이코노미**: 출석·미션·광고 적립, 상단 노출권·수수료 할인쿠폰 소모
- **알림**: 입찰 경쟁·낙찰·정산·신고 처리 이벤트
- **신고**: 접수 검증 + 인용 시 대상 제재(삭제/계정 비활성화)
- **리뷰**: 완료된 거래 당사자만 작성
- **마이페이지**: `GET /users/me/dashboard` 활동 요약
- **AI 보조**: 과거 낙찰가 기반 시세 추천, 규칙 기반 어뷰징 문구 탐지 (LLM Gateway 는 분리 예정)

기능별 엔드포인트와 정책은 [`backend/README.md`](backend/README.md) 참고.

## 빠른 시작

```bash
# 1) 백엔드
cd backend
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env
# alembic 마이그레이션을 쓰려면: .env 에 AUTO_CREATE_TABLES=false 후 `alembic upgrade head`
uvicorn app.main:app --reload                      # http://localhost:8000
pytest                                             # 테스트

# 2) 프론트엔드 (새 터미널)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                                        # http://localhost:3000
```

백엔드 API 문서: http://localhost:8000/docs

## Docker

전체 스택(PostgreSQL + Redis + 백엔드 + 프론트엔드)을 한 번에 띄운다.

```bash
docker compose up --build          # http://localhost:3000 , API http://localhost:8000
docker compose down -v             # 정리 (DB 볼륨 포함)
```

- 백엔드 컨테이너는 기동 시 `alembic upgrade head` 로 스키마를 맞춘 뒤 실행된다.
- 호스트 포트 충돌 시 `DB_PORT` / `BACKEND_PORT` / `FRONTEND_PORT` 로 재지정한다
  (예: `DB_PORT=55432 docker compose up`).
- `SECRET_KEY` 는 환경변수로 주입한다 (미지정 시 개발용 기본값).

## 참고

- 프론트엔드는 각 API 엔드포인트를 호출해 응답(JSON)을 그대로 보여주는 수준입니다. UI/디자인 작업은 하지 않았습니다.
- `.env`, `.env.local`, 가상환경, `node_modules`, AI 도구 설정 파일 등은 git 에 커밋되지 않습니다 (`.gitignore` 참고).
