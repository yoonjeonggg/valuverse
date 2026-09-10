import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 이미지용 독립 실행 번들
  output: "standalone",
};

export default nextConfig;
