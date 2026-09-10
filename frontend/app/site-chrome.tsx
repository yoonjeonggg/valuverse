"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, getToken } from "./lib/api";

const NAV: [string, string][] = [
  ["/items", "일반경매"],
  ["/skill-items", "스킬"],
  ["/predictions", "예측시장"],
  ["/points", "포인트"],
  ["/notifications", "알림"],
  ["/reviews", "리뷰"],
  ["/reports", "신고"],
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="nav">
      {NAV.map(([href, label]) => {
        const active = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link key={href} href={href} aria-current={active ? "page" : undefined}>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function HeaderAuth() {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [points, setPoints] = useState<number | null>(null);

  useEffect(() => {
    // localStorage(외부 시스템)의 토큰을 읽어 렌더에 반영
    const token = getToken();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSignedIn(!!token);
    setReady(true);
    if (!token) return;
    api<{ points: number }>("/users/me", { auth: true })
      .then((u) => setPoints(u.points))
      .catch(() => setPoints(null));
  }, []);

  if (!ready) return <span style={{ width: 88 }} />;

  if (!signedIn)
    return (
      <div className="header-right">
        <Link className="btn btn-sm" href="/auth">
          로그인
        </Link>
      </div>
    );

  return (
    <div className="header-right">
      {points !== null && (
        <span className="pointpill">{points.toLocaleString()} P</span>
      )}
      <Link className="btn btn-sm" href="/me">
        내 계정
      </Link>
    </div>
  );
}
