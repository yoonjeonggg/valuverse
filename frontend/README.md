# Valuverse Frontend

Next.js(App Router) 기반. 랜딩 페이지 + 기능별 API 콘솔 화면.

- 폰트: Wanted Sans (jsDelivr CDN)
- 테마: 레드 액센트 + 페이퍼 배경, 디자인 토큰은 `app/globals.css` 상단 `:root`
- 아이콘: 인라인 SVG (`app/lib/ui.tsx`의 `Icon`)
- 기능 화면은 각 엔드포인트를 호출해 응답(JSON)을 인스펙터에 그대로 보여줍니다.

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
  globals.css    디자인 토큰 + 컴포넌트 스타일
  site-chrome.tsx 헤더 네비게이션 / 로그인 상태 (클라이언트)
  lib/api.ts     fetch 래퍼 + 토큰(localStorage) 관리
  lib/format.ts  toIso 등 포맷 헬퍼
  lib/ui.tsx     UI 컴포넌트 (useCall, Result, Field, Section, PageHeader, Icon)
  page.tsx       랜딩 (히어로 + 진행 중인 경매)
  auth/          POST /auth/signup, POST /auth/login (토큰 저장)
  me/            /users/me (조회/수정/탈퇴), /users/{id}
  items/         일반경매: item CRUD, 입찰, 블라인드 입찰, 낙찰/즉시구매/조기마감/상단노출권, 실시간 입찰(WS)
  skill-items/   스킬상품: skill-item CRUD, 예약(낙찰), 완료 정산/노쇼, 에스크로
  predictions/   예측명제 CRUD(관리자), 베팅, 파리뮤추얼 배당률/정산
  points/        포인트 잔액/내역, 출석·미션·광고 적립, 관리자 수동 조정
  notifications/ 알림 조회 / 읽음 처리
  reviews/       리뷰 CRUD
  reports/       신고 생성 / 관리자 조회·처리(제재 연동)
```

## 인증

로그인(`/auth`)하면 액세스 토큰이 `localStorage` 에 저장되고, 이후 인증이 필요한
호출에 자동으로 `Authorization: Bearer` 헤더가 붙습니다. 관리자 전용 API(예측명제
등록/수정, 신고 조회/처리)는 `is_admin=true` 계정으로 로그인해야 합니다
(첫 관리자 지정은 `../backend/README.md` 참고).
