# Valuverse

AI 경매 플랫폼. `기능명세서 기본ver[CRUD]` 범위 구현.

| 디렉터리 | 내용 |
|---|---|
| [`backend/`](backend/README.md) | FastAPI + SQLAlchemy. 회원 / 일반경매 / 블라인드 입찰 / 스킬상품·예약·에스크로 / 예측명제·베팅 / 포인트 / 리뷰 / 신고 CRUD API |
| [`frontend/`](frontend/README.md) | Next.js. **디자인 없이** 백엔드 API 연동만 확인하는 최소 화면 |

## 빠른 시작

```bash
# 1) 백엔드
cd backend
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload                      # http://localhost:8000

# 2) 프론트엔드 (새 터미널)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                                        # http://localhost:3000
```

백엔드 API 문서: http://localhost:8000/docs

## 참고

- 현재 프론트엔드는 각 API 엔드포인트를 호출해 응답(JSON)을 그대로 보여주는
  수준입니다. UI/디자인 작업은 하지 않았습니다.
- `.env`, `.env.local`, 가상환경, `node_modules`, AI 도구 설정 파일 등은
  git 에 커밋되지 않습니다 (`.gitignore` 참고).
