"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "./api";
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

/** 로그인 사용자 정보. 비로그인이거나 조회에 실패하면 null. */
export function useMe(): Me | null {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    if (!getToken()) return;
    fetchMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);
  return me;
}
