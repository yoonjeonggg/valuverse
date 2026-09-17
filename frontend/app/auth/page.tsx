"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, getToken, setToken } from "../lib/api";
import { Card, PageHeader, useCall } from "../lib/ui";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [signedIn, setSignedIn] = useState(!!getToken());

  const signup = useCall(() =>
    api("/auth/signup", { method: "POST", body: { email, password, nickname } }),
  );
  const submitSignup = async () => {
    const res = await signup.run();
    if (res) setMode("login");
  };

  const login = useCall(async () => {
    const res = await api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(res.access_token);
    return res;
  });
  const submitLogin = async () => {
    const res = await login.run();
    if (res) {
      setSignedIn(true);
      router.push("/me");
    }
  };

  const logout = () => {
    setToken(null);
    setSignedIn(false);
  };

  if (signedIn) {
    return (
      <div>
        <PageHeader eyebrow="Account" title="로그인 상태" />
        <Card title="로그인 되어 있습니다">
          <div className="actions">
            <button onClick={logout}>로그아웃</button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader eyebrow="Account" title="회원가입 / 로그인">
        <p>로그인하면 이후 인증이 필요한 요청에 자동으로 로그인 상태가 유지됩니다.</p>
      </PageHeader>

      <Card
        title={mode === "login" ? "로그인" : "회원가입"}
        right={
          <button className="btn-sm" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "계정이 없으신가요? 회원가입" : "이미 계정이 있으신가요? 로그인"}
          </button>
        }
      >
        <div className="field">
          <span>이메일</span>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="user@example.com" />
        </div>
        <div className="field">
          <span>비밀번호</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8~64자"
          />
        </div>
        {mode === "signup" && (
          <div className="field">
            <span>닉네임</span>
            <input value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="2~20자" />
          </div>
        )}
        <div className="actions">
          {mode === "login" ? (
            <button className="btn btn-primary" onClick={submitLogin} disabled={login.loading}>
              로그인
            </button>
          ) : (
            <button className="btn btn-primary" onClick={submitSignup} disabled={signup.loading}>
              가입하기
            </button>
          )}
        </div>
        {mode === "login" && login.error && <p className="hint hint--error">{login.error}</p>}
        {mode === "signup" && signup.error && <p className="hint hint--error">{signup.error}</p>}
        {mode === "signup" && signup.data !== null && signup.data !== undefined && !signup.error && (
          <p className="hint">가입이 완료되었습니다. 로그인해 주세요.</p>
        )}
      </Card>
    </div>
  );
}
