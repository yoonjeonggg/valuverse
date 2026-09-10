import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { SiteNav, HeaderAuth } from "./site-chrome";

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
            <HeaderAuth />
          </div>
        </header>

        <main className="shell">{children}</main>

        <footer className="site-footer">
          <div className="site-footer__inner">
            <div>
              <b>Valuverse</b>
              차별화된 경매 메커니즘과
              <br />
              포인트 이코노미를 결합한 거래 플랫폼.
            </div>
            <div>
              <b>거래</b>
              <Link href="/items">일반·블라인드 경매</Link>
              <br />
              <Link href="/skill-items">스킬 경매 / 에스크로</Link>
            </div>
            <div>
              <b>리텐션</b>
              <Link href="/predictions">예측시장</Link>
              <br />
              <Link href="/points">포인트 · 쿠폰</Link>
            </div>
            <div>
              <b>개발</b>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
              >
                API 문서 (Swagger)
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
