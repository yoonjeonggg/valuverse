import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";
import { SiteNav, HeaderNotifications, HeaderAuth, ThemeToggle } from "./site-chrome";

// 명시적으로 저장된 선택이 있을 때만 속성을 세팅한다. 저장된 값이 없으면
// (대다수 첫 방문자) globals.css 의 `color-scheme: light dark` + `light-dark()` 가
// OS 설정을 그대로 반영하므로 이 스크립트는 아무 작업도 하지 않는다 -- matchMedia
// 호출이나 style 재계산을 그만큼 건너뛴다.
const THEME_INIT_SCRIPT = `
try {
  var t = localStorage.getItem("valuverse_theme");
  if (t === "light" || t === "dark") {
    document.documentElement.setAttribute("data-theme", t);
  }
} catch (e) {}
`;

export const metadata: Metadata = {
  title: "Valuverse — 경매 플랫폼",
  description:
    "실시간 경매, 밀봉 입찰, 재능 거래, 포인트 예측시장을 한곳에서. Valuverse.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
        <header className="site-header">
          <div className="site-util">
            <HeaderNotifications />
            <HeaderAuth />
            <ThemeToggle />
          </div>
          <div className="site-header__bar">
            <Link href="/" className="wordmark">
              Valu<b>verse</b>
            </Link>
            <SiteNav />
          </div>
        </header>

        <main className="shell">{children}</main>

        <footer className="site-footer">
          <div className="site-footer__inner">
            <Link href="/" className="wordmark">
              Valu<b>verse</b>
            </Link>
            <nav className="site-footer__links" aria-label="바로가기">
              <Link href="/items">일반 · 블라인드 경매</Link>
              <Link href="/skill-items">스킬 경매</Link>
              <Link href="/predictions">예측시장</Link>
              <Link href="/points">포인트 센터</Link>
              <Link href="/reports">신고하기</Link>
            </nav>
            <div className="site-footer__note">
              <span>마감 직전에 입찰이 들어오면 마감 시간이 자동으로 연장됩니다.</span>
              <span>&copy; 2026 Valuverse</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
