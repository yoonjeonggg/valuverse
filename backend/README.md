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

## 관리자 계정

예측명제 등록/수정, 신고 조회/처리는 관리자 권한이 필요하다. 첫 관리자는 DB 에서 직접 지정한다.

```bash
python -c "from app.database import SessionLocal; from app.models.user import User; \
db=SessionLocal(); db.query(User).filter(User.email=='you@example.com').update({'is_admin': True}); db.commit()"
```

## 참고

- 본 구현은 기본 CRUD 범위만 다룬다. AI 기능·실시간 입찰 로직·자동연장·배당 정산 등은 제외.
- 블라인드 입찰 금액은 마감 전까지 응답에 노출하지 않는다(접근 제어).
