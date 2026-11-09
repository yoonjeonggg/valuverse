import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 이미지용 독립 실행 번들. Vercel 은 자체 빌드 방식과 충돌하므로 끈다 (VERCEL=1 자동 주입).
  output: process.env.VERCEL ? undefined : "standalone",
  async headers() {
    return [
      {
        // 폰트 경로에 버전이 들어 있어 내용이 바뀌면 경로도 바뀐다 -> 1년 캐시해도 안전.
        source: "/fonts/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default nextConfig;
