import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Valuverse - 백엔드 연동",
  description: "백엔드 API 연동 확인용 최소 프론트엔드",
};

const NAV: [string, string][] = [
  ["/", "홈"],
  ["/auth", "회원/인증"],
  ["/me", "내 정보"],
  ["/items", "일반경매"],
  ["/skill-items", "스킬상품"],
  ["/predictions", "예측/베팅"],
  ["/points", "포인트"],
  ["/reviews", "리뷰"],
  ["/reports", "신고"],
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <header style={{ borderBottom: "1px solid #ccc", padding: 8 }}>
          <strong>Valuverse</strong> — 백엔드 연동 확인용
          <nav style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 12 }}>
            {NAV.map(([href, label]) => (
              <Link key={href} href={href}>
                {label}
              </Link>
            ))}
          </nav>
        </header>
        <main style={{ padding: 12, maxWidth: 900 }}>{children}</main>
      </body>
    </html>
  );
}
