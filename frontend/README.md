# Valuverse Frontend (백엔드 연동 확인용)

Next.js(App Router) 기반. **디자인은 없습니다.** 백엔드(`../backend`)에 구현된
API가 실제로 호출되는지 확인하기 위한 최소 화면만 있습니다.

## 실행

```bash
npm install
cp .env.local.example .env.local   # 필요 시 API 주소 수정
npm run dev
```

- 화면: http://localhost:3000
- 백엔드가 http://localhost:8000 에서 떠 있어야 합니다 (`../backend/README.md` 참고).

## 환경 변수

| 키 | 설명 | 기본값 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 API 주소 | `http://localhost:8000` |

`.env.local` 은 git 에 커밋되지 않습니다. `.env.local.example` 을 복사해 사용하세요.

## 구조

```
app/
  lib/api.ts     fetch 래퍼 + 토큰(localStorage) 관리
  lib/ui.tsx     연동 확인용 최소 UI 헬퍼 (useCall, Result, Field, Section)
  page.tsx       홈 / 헬스체크
  auth/          POST /auth/signup, POST /auth/login (토큰 저장)
  me/            /users/me (조회/수정/탈퇴), /users/{id}
  items/         일반경매: item CRUD, 입찰, 블라인드 입찰
  skill-items/   스킬상품: skill-item CRUD, 예약, 에스크로
  predictions/   예측명제 CRUD(관리자), 베팅
  points/        포인트 잔액/내역/트랜잭션
  reviews/       리뷰 CRUD
  reports/       신고 생성 / 관리자 조회·처리
```

## 인증

로그인(`/auth`)하면 액세스 토큰이 `localStorage` 에 저장되고, 이후 인증이 필요한
호출에 자동으로 `Authorization: Bearer` 헤더가 붙습니다. 관리자 전용 API(예측명제
등록/수정, 신고 조회/처리)는 `is_admin=true` 계정으로 로그인해야 합니다
(첫 관리자 지정은 `../backend/README.md` 참고).
