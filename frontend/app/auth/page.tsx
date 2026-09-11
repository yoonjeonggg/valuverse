"use client";

import { useState } from "react";
import { api, getToken, setToken } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Account" title="회원 / 인증">
        <p>
          로그인하면 액세스 토큰이 브라우저에 저장되고, 이후 인증이 필요한 요청에
          자동으로 첨부됩니다.
        </p>
      </PageHeader>

      <Section title="계정 정보">
        <Field
          label="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@example.com"
        />
        <Field
          label="비밀번호 (8~64자)"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Field
          label="닉네임 (2~20자, 가입용)"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
        />
      </Section>

      <Section title="회원가입" method="POST /auth/signup">
        <div className="actions">
          <button className="btn-primary" onClick={() => signup.run()}>
            가입하기
          </button>
        </div>
        <Result {...signup} />
      </Section>

      <Section title="로그인" method="POST /auth/login">
        <div className="actions">
          <button className="btn-primary" onClick={() => login.run()}>
            로그인
          </button>
        </div>
        <Result {...login} />
      </Section>

      <Section title="현재 토큰">
        <p className="hint" style={{ wordBreak: "break-all" }}>
          {tokenState ?? "저장된 토큰이 없습니다."}
        </p>
        <div className="actions">
          <button
            onClick={() => {
              setToken(null);
              setTokenState(null);
            }}
          >
            로그아웃 (토큰 삭제)
          </button>
        </div>
      </Section>
    </div>
  );
}
