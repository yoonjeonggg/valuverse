# ValueVerse Frontend 개발 문서

프론트엔드를 개발할 때 참고하는 문서입니다. 프로젝트 소개와 전체 구조는 [루트 README](../README.md)를 봅니다.

## 스택

- Next.js (App Router), React, TypeScript, Tailwind CSS
- 폰트: Noto Sans KR, `next/font/google` 로 빌드 시 받아 자체 호스팅 (`app/layout.tsx`)
- 아이콘: 인라인 SVG (`app/lib/ui.tsx`의 `Icon`)

## 실행

Node.js 22 기준입니다 (CI 와 동일).

```bash
npm install
cp .env.local.example .env.local   # 필요 시 API 주소 수정
npm run dev
```

- 화면: http://localhost:3000
- 백엔드가 http://localhost:8000 에서 떠 있어야 합니다 ([`../backend/README.md`](../backend/README.md) 참고).

CI 와 같은 검사는 아래로 실행합니다.

```bash
npx eslint app/
npm run build
```

## 환경 변수

| 키 | 설명 | 기본값 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 API 주소 (브라우저용, 빌드 시 고정) | `http://localhost:8000` |
| `INTERNAL_API_BASE_URL` | 서버 렌더링 시 백엔드 주소 (컨테이너 내부망 등). 생략 시 위 값 사용 | — |

`.env.local` 은 git 에 커밋되지 않습니다. `.env.local.example` 을 복사해 사용하세요.

## 구조

```
app/
  layout.tsx       루트 레이아웃, 폰트, 테마 초기화 스크립트
  globals.css      디자인 토큰 + 컴포넌트 스타일
  site-chrome.tsx  헤더 네비게이션 / 알림 / 로그인 상태 / 테마 토글 (클라이언트)
  page.tsx         홈 (서버 컴포넌트, 화면은 home-view.tsx)
  lib/
    api.ts         fetch 래퍼, 토큰(localStorage) 관리, AUTH_CHANGED / POINTS_CHANGED 이벤트
    server-api.ts  서버 컴포넌트용 조회
    me.ts          로그인 사용자 (useMe, useHasToken)
    types.ts       API 응답 공용 타입
    ui.tsx         공용 훅·컴포넌트 (useCall, useLoad, Loadable, Field, SelectField,
                   ErrorText, Card, Countdown, PageHeader, Icon)
    cards.tsx      경매 / 스킬 카드
    chat-widget.tsx 입찰 상담 챗봇
    format.ts      toIso, formatDateTime
  items/           일반·블라인드 경매 목록, 상세, 실시간 입찰
  skill-items/     스킬 경매 목록, 상세, 예약
  predictions/     예측시장 목록, 베팅
  points/          포인트 센터 (출석, 미션, 광고, 쿠폰)
  me/              마이페이지
  notifications/   알림
  reviews/         리뷰
  reports/         신고
  admin/           관리자 대시보드
  auth/            로그인 / 회원가입
```

## 화면 작성 규칙

- **공개 화면**(홈, 경매/스킬/예측 목록과 상세)은 `page.tsx`(서버 컴포넌트)가 첫 데이터를 받아 HTML 에 담고,
  화면 로직은 `*-view.tsx`(클라이언트 컴포넌트)에 둡니다.
- **로그인이 필요한 화면**(마이페이지, 포인트 등)은 토큰이 localStorage 에 있어 서버에서 알 수 없으므로 브라우저에서 불러옵니다.
- 조회는 `useLoad` + `Loadable` 로 처리해 로딩 / 실패(다시 시도) / 빈 목록을 구분합니다. 조회 실패를 빈 목록으로 숨기지 않습니다.
- 등록·수정처럼 사용자 동작으로 호출하는 요청은 `useCall` 을 씁니다.
- 날짜는 서버/브라우저 렌더 결과가 같아야 하므로 `formatDateTime`(Asia/Seoul 고정)으로 표시합니다.
- API 응답 타입은 `lib/types.ts` 에 모읍니다.

## 디자인 토큰

- 색상은 `app/globals.css` 상단 `:root` 의 토큰을 씁니다. 웜톤 아이보리 바탕 + 브랜드 레드입니다.
- 토큰은 `light-dark(라이트값, 다크값)` 로 한 줄에 정의해 다크 변형이 빠지지 않게 합니다.
- 테마는 기본적으로 OS 설정을 따르고, `<html data-theme>` 가 붙으면 그쪽으로 고정됩니다
  (`layout.tsx` 인라인 스크립트 + `site-chrome.tsx` 의 `ThemeToggle`).
- `--red` 는 글자·밑줄용, `--red-solid` 는 흰 글자를 얹는 면(주요 버튼 등)용입니다.

## 성능

- 서버 조회가 실패하거나 1.5초를 넘기면 브라우저에서 다시 불러옵니다 (`lib/server-api.ts`).
- 목록은 카드에 필요한 필드만 HTML 에 싣습니다 (`lib/cards.tsx` 의 `toAuctionCardItem` 등).

## 인증

로그인(`/auth`)하면 액세스 토큰이 `localStorage` 에 저장되고, 이후 인증이 필요한
호출에 자동으로 `Authorization: Bearer` 헤더가 붙습니다. 로그인·로그아웃·401 만료는
`AUTH_CHANGED` 이벤트로 전파되어 새로고침 없이 화면에 반영됩니다.

관리자 전용 기능(예측명제 등록/수정, 신고 조회/처리)은 `is_admin=true` 계정으로 로그인해야 합니다
(첫 관리자 지정은 [`../backend/README.md`](../backend/README.md) 참고).
