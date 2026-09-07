"use client";

import { useState } from "react";
import { api, getToken, setToken } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [tokenState, setTokenState] = useState<string | null>(getToken());

  const signup = useCall(() =>
    api("/auth/signup", {
      method: "POST",
      body: { email, password, nickname },
    }),
  );

  const login = useCall(async () => {
    const res = await api<{ access_token: string; token_type: string }>(
      "/auth/login",
      { method: "POST", body: { email, password } },
    );
    setToken(res.access_token);
    setTokenState(res.access_token);
    return res;
  });

  return (
    <div>
      <h1>회원 / 인증</h1>

      <Section title="공통 입력">
        <Field
          label="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@example.com"
        />
        <Field
          label="password (8~64자)"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Field
          label="nickname (2~20자, 가입용)"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
        />
      </Section>

      <Section title="POST /auth/signup">
        <button onClick={() => signup.run()}>가입</button>
        <Result data={signup.data} error={signup.error} loading={signup.loading} />
      </Section>

      <Section title="POST /auth/login">
        <button onClick={() => login.run()}>로그인 (토큰 저장)</button>
        <Result data={login.data} error={login.error} loading={login.loading} />
      </Section>

      <Section title="현재 토큰">
        <p style={{ wordBreak: "break-all", fontSize: 12 }}>
          {tokenState ?? "(없음)"}
        </p>
        <button
          onClick={() => {
            setToken(null);
            setTokenState(null);
          }}
        >
          로그아웃 (토큰 삭제)
        </button>
      </Section>
    </div>
  );
}
