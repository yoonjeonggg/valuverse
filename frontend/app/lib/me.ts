"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { AUTH_CHANGED, api, getToken } from "./api";
import type { Me } from "./types";

// 헤더(내비/잔액)와 페이지가 한 화면에서 동시에 /users/me 를 부르므로 진행 중인 요청을
// 공유한다. 끝난 응답은 캐시하지 않는다: 다른 화면에서 잔액 등이 바뀐 뒤 들어온 페이지는
// 새로 받아야 한다.
let inflight: Promise<Me> | null = null;

export function fetchMe(): Promise<Me> {
  if (!inflight) {
    inflight = api<Me>("/users/me", { auth: true }).finally(() => {
      inflight = null;
    });
  }
  return inflight;
}

/** 로그인 사용자 정보. 비로그인이거나 조회에 실패하면 null. 로그인/로그아웃을 따라간다. */
export function useMe(): Me | null {
  const hasToken = useHasToken();
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    if (!hasToken) return;
    let alive = true;
    fetchMe()
      .then((u) => alive && setMe(u))
      .catch(() => alive && setMe(null));
    return () => {
      alive = false;
      // 다른 계정으로 다시 로그인했을 때 이전 사용자 정보가 잠깐 보이지 않게 비운다.
      setMe(null);
    };
  }, [hasToken]);
  return hasToken ? me : null;
}

function subscribeAuth(onChange: () => void) {
  window.addEventListener(AUTH_CHANGED, onChange);
  // 다른 탭에서 로그인/로그아웃한 경우
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(AUTH_CHANGED, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * 로그인 토큰 보유 여부. 서버 렌더링/hydration 중에는 알 수 없으므로 null.
 * (localStorage 를 렌더 중에 바로 읽으면 서버 HTML 과 달라 hydration 오류가 난다.)
 */
export function useHasToken(): boolean | null {
  return useSyncExternalStore(
    subscribeAuth,
    () => getToken() !== null,
    () => null,
  );
}
