"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, getToken } from "./lib/api";
import { Icon } from "./lib/ui";

const NAV: [string, string][] = [
  ["/items", "일반경매"],
  ["/skill-items", "스킬"],
  ["/predictions", "예측시장"],
  ["/points", "포인트"],
  ["/reviews", "리뷰"],
  ["/reports", "신고"],
];

export function SiteNav() {
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (!getToken()) return;
    api<{ is_admin: boolean }>("/users/me", { auth: true })
      .then((u) => setIsAdmin(u.is_admin))
      .catch(() => {});
  }, []);

  const items = isAdmin ? [...NAV, ["/admin", "관리자"] as [string, string]] : NAV;

  return (
    <nav className="nav">
      {items.map(([href, label]) => {
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

const THEME_KEY = "valuverse_theme";

// 명시적으로 고른 테마가 있으면 그 값, 없으면(대다수) 시스템 설정을 따른다.
// data-theme 속성이 비어 있을 수 있는 건 layout.tsx 의 인라인 스크립트가
// "선택된 값이 있을 때만" 세팅하도록 최소화됐기 때문 -- globals.css 의
// light-dark() 가 이 경우 이미 시스템 설정대로 렌더링해두었으므로, 여기서는
// 토글 아이콘이 그 실제 상태와 어긋나지 않도록 matchMedia 로 같은 값을 읽어온다.
function effectiveTheme(): "light" | "dark" {
  const explicit = document.documentElement.getAttribute("data-theme");
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeToggle() {
  // 서버 렌더링과 동일하게 "light" 로 시작해 hydration mismatch 를 피하고,
  // 마운트 직후 실제 값으로 한 번만 동기화한다.
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(effectiveTheme());
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      /* ignore */
    }
  };

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"}
    >
      <Icon name={theme === "dark" ? "sun" : "moon"} />
    </button>
  );
}

export function HeaderNotifications() {
  const [signedIn, setSignedIn] = useState(false);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const token = getToken();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSignedIn(!!token);
    if (!token) return;
    api<{ unread: number }>("/users/me/notifications/unread-count", { auth: true })
      .then((r) => setUnread(r.unread))
      .catch(() => {});
  }, []);

  if (!signedIn) return null;

  return (
    <Link href="/notifications" className="bell-btn" aria-label="알림">
      <Icon name="bell" size={19} />
      {unread > 0 && <span className="bell-badge">{unread > 9 ? "9+" : unread}</span>}
    </Link>
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
      <Link className="btn btn-sm" href="/auth">
        로그인
      </Link>
    );

  return (
    <>
      {points !== null && (
        <span className="pointpill">{points.toLocaleString()} P</span>
      )}
      <Link className="btn btn-sm" href="/me">
        내 계정
      </Link>
    </>
  );
}
