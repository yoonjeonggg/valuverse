import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { SiteNav, HeaderNotifications, HeaderAuth } from "./site-chrome";

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
    <html lang="ko">
      <body>
        <header className="site-header">
          <div className="site-header__bar">
            <Link href="/" className="wordmark">
              Valu<b>verse</b>
            </Link>
            <SiteNav />
            <div className="header-right">
              <HeaderNotifications />
              <HeaderAuth />
            </div>
          </div>
        </header>

        <main className="shell">{children}</main>

        <footer className="site-footer">
          <div className="site-footer__inner">
            <div className="site-footer__brand">
              <Link href="/" className="wordmark">
                Valu<b>verse</b>
              </Link>
              <p>
                차별화된 경매 메커니즘과 포인트 이코노미를 결합한 거래
                플랫폼.
              </p>
            </div>
            <nav className="site-footer__col">
              <b>거래</b>
              <ul>
                <li>
                  <Link href="/items">일반·블라인드 경매</Link>
                </li>
                <li>
                  <Link href="/skill-items">스킬 경매 / 에스크로</Link>
                </li>
              </ul>
            </nav>
            <nav className="site-footer__col">
              <b>리텐션</b>
              <ul>
                <li>
                  <Link href="/predictions">예측시장</Link>
                </li>
                <li>
                  <Link href="/points">포인트 · 쿠폰</Link>
                </li>
              </ul>
            </nav>
          </div>
          <div className="site-footer__bottom">
            <span>&copy; 2026 Valuverse</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
