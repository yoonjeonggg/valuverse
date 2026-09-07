"use client";

import { useEffect, useState } from "react";
import { api, API_BASE_URL, getToken } from "./lib/api";
import { Result, Section, useCall } from "./lib/ui";

export default function Home() {
  const health = useCall(() => api("/health"));
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    // localStorage(외부 시스템)의 토큰 존재 여부를 화면에 반영
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHasToken(!!getToken());
    health.run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h1>백엔드 연동 확인</h1>
      <p>
        이 프론트엔드는 디자인 없이 백엔드 API 연동만 확인하기 위한 것입니다.
      </p>
      <ul>
        <li>
          API 주소: <code>{API_BASE_URL}</code> (환경변수{" "}
          <code>NEXT_PUBLIC_API_BASE_URL</code> 로 변경)
        </li>
        <li>로그인 토큰: {hasToken ? "저장됨" : "없음 (회원/인증 탭에서 로그인)"}</li>
        <li>
          Swagger 문서: <code>{API_BASE_URL}/docs</code>
        </li>
      </ul>

      <Section title="GET /health">
        <button onClick={() => health.run()}>다시 확인</button>
        <Result data={health.data} error={health.error} loading={health.loading} />
      </Section>
    </div>
  );
}
