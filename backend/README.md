# AI 경매 플랫폼 API (FastAPI)

「기능명세서 기본ver[CRUD]」 범위의 백엔드 구현. 회원 / 일반경매 상품·입찰 / 블라인드 입찰 /
스킬상품·예약·에스크로 / 예측명제·베팅 / 포인트 / 리뷰 / 신고 엔티티의 기본 CRUD 를 제공한다.

## 스택

- FastAPI + Uvicorn
- SQLAlchemy 2.0 (기본 SQLite)
- Pydantic v2 / pydantic-settings
- JWT 인증 (python-jose), 비밀번호 해시 (passlib + bcrypt)

## 실행

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

cp .env.example .env             # 값 채우기 (아래 참고)
uvicorn app.main:app --reload
```

- API 문서: http://127.0.0.1:8000/docs
- 헬스체크: http://127.0.0.1:8000/health

## 환경 변수 (`.env`)

`.env` 는 git 에 커밋되지 않는다. `.env.example` 을 복사해서 사용한다.

| 키 | 설명 | 기본값 |
|---|---|---|
| `SECRET_KEY` | JWT 서명 키. **운영에서는 반드시 재정의** | `dev-secret-change-me` |
| `ALGORITHM` | JWT 알고리즘 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 액세스 토큰 만료(분) | `1440` |
| `DATABASE_URL` | DB 접속 URL | `sqlite:///./auction.db` |
| `AUCTION_EXTEND_WINDOW_SECONDS` | 마감 임박 판정 구간(초) | `180` |
| `AUCTION_EXTEND_BY_SECONDS` | 자동 연장 시간(초) | `180` |
| `AUCTION_MAX_EXTENSIONS` | 자동 연장 최대 횟수 | `10` |

키 생성:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 프로젝트 구조

```
app/
  core/        설정(config), 보안(security), 의존성(deps), 시간 유틸
  models/      SQLAlchemy 모델
  schemas/     Pydantic 요청/응답 스키마
  services/    비즈니스 로직
  routers/     엔드포인트
  database.py  엔진 / 세션
  main.py      앱 엔트리포인트
```

## 낙찰/정산 로직 (CRUD 이후 추가)

기본 CRUD 위에 「개발명세서」 Phase 1~3 / 「기획서」 로드맵 1·2·4단계의 정산 로직을 얹었다.

| 기능 | 엔드포인트 | 설명 |
|---|---|---|
| 즉시구매 | `POST /items/{id}/buy-now` | 즉시구매가로 즉시 낙찰, 경매 마감 |
| 조기 마감 | `POST /items/{id}/close` | 판매자가 경매를 마감하고 최고 입찰자를 낙찰자로 확정 |
| 자동 연장 | (입찰 시 자동) | 마감 임박 입찰이면 마감시간을 연장 (FR-AUC-03, 스나이핑 방지) |
| 자동 마감 | (조회 시 자동) | `end_time` 이 지난 경매는 조회 시 낙찰 확정 처리 |
| 배당률 조회 | `GET /predictions/{id}/odds` | 현재 베팅 풀 기준 파리뮤추얼 배당 배수 (FR-PRD-03) |
| 명제 정산 | `POST /predictions/{id}/settle` | 관리자, 결과 확정 후 승자에게 파리뮤추얼 배당 포인트 지급 (FR-PRD-04) |
| 스킬 예약(낙찰) | `POST /skill-bookings` | 판매자가 낙찰가로 예약 생성. 구매자 포인트가 차감돼 에스크로에 보관 (FR-SKL-02·03) |
| 스킬 완료 정산 | `POST /skill-bookings/{id}/complete` | 구매자가 완료 확인 → 에스크로를 판매자에게 정산 |
| 스킬 노쇼 | `POST /skill-bookings/{id}/no-show` | 판매자 노쇼면 구매자 환불, 구매자 노쇼면 판매자 정산 (FR-SKL-05) |
| 출석 체크 | `POST /points/check-in` | 하루 1회, 연속 출석 보너스 (FR-PRD-05) |
| 미션 | `GET /points/missions`, `POST /points/missions/{key}/claim` | 첫 입찰·첫 등록·첫 리뷰 달성 시 보상 (FR-PRD-06) |
| 광고 보상 | `POST /points/ad-reward` | 하루 N회 한도 내 포인트 지급 (FR-PRD-07) |
| 상단 노출권 | `POST /items/{id}/spotlight` | 포인트로 구매, 24시간 동안 목록 상단 노출 (FR-PRD-08) |
| 알림 | `GET /users/me/notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all` | 입찰 경쟁·낙찰·스킬 정산·예측 정산 시 자동 생성 (FR-COM-03) |

- 상품 등록 시 `auction_type`(`general`/`blind`)을 지정한다. 타입이 맞지 않는 입찰은 거부된다.
- 블라인드 경매 낙찰 규칙은 `blind_price_rule` 로 정한다: `first`(제시가 그대로) / `second`(Vickrey, 2위 금액으로 결제, FR-BLD-04). 입찰자가 1명이면 본인 제시가.
- 정산 시 승리 포지션 풀이 비어 있으면 전원 원금 환불한다.
- 스킬 예약 취소(`DELETE /skill-bookings/{id}`) 시 보관중 에스크로는 구매자에게 환불된다.
- 에스크로 상태 변경(`PATCH /escrows/{id}`)은 실제 포인트 이동을 동반한다.
- 포인트는 출석·미션·광고로만 적립된다. 수동 조정(`POST /point-transactions`)은 관리자 전용이다.

## 테스트

```bash
pip install -r requirements.txt   # pytest 포함
pytest
```

`tests/` 는 인메모리 SQLite 로 격리 실행된다. 낙찰·자동연장·파리뮤추얼 정산 시나리오를 커버한다.

## 관리자 계정

예측명제 등록/수정, 신고 조회/처리는 관리자 권한이 필요하다. 첫 관리자는 DB 에서 직접 지정한다.

```bash
python -c "from app.database import SessionLocal; from app.models.user import User; \
db=SessionLocal(); db.query(User).filter(User.email=='you@example.com').update({'is_admin': True}); db.commit()"
```

## 참고

- 본 구현은 기본 CRUD 범위만 다룬다. AI 기능·실시간 입찰 로직·자동연장·배당 정산 등은 제외.
- 블라인드 입찰 금액은 마감 전까지 응답에 노출하지 않는다(접근 제어).
