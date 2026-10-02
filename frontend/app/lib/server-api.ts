// 서버 컴포넌트 전용: 공개 데이터를 렌더 전에 받아 HTML 에 담는다.
// 브라우저가 JS 를 받고 나서야 API 를 부르던 대기(HTML -> JS -> API)를 없애고,
// 데이터가 늦게 끼어들며 레이아웃이 밀리는 것도 막는다.
//
// 실패하거나 느리면 null 을 돌려주고, 그 경우 화면은 예전처럼 브라우저에서 다시 불러온다.

import { API_BASE_URL, buildUrl, type Query } from "./api";

// 컨테이너 안에서는 브라우저용 주소(localhost)로 백엔드에 닿지 않으므로 내부 주소를 따로 둔다.
const INTERNAL_BASE =
  process.env.INTERNAL_API_BASE_URL?.replace(/\/$/, "") || API_BASE_URL;

// 백엔드가 느려도 페이지 응답이 이 이상 늦어지지 않게 한다.
const TIMEOUT_MS = 1500;

export async function serverGet<T>(path: string, query?: Query): Promise<T | null> {
  try {
    const res = await fetch(buildUrl(INTERNAL_BASE, path, query), {
      // 가격/상태가 실시간으로 바뀌므로 캐시하지 않는다.
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
