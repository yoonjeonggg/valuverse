"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function MePage() {
  const [nickname, setNickname] = useState("");
  const [profileImage, setProfileImage] = useState("");
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState("");

  const me = useCall(() => api("/users/me", { auth: true }));
  const dashboard = useCall(() => api("/users/me/dashboard", { auth: true }));
  const update = useCall(() =>
    api("/users/me", {
      method: "PATCH",
      auth: true,
      body: {
        nickname: nickname || undefined,
        profile_image: profileImage || undefined,
        password: password || undefined,
      },
    }),
  );
  const remove = useCall(() =>
    api("/users/me", { method: "DELETE", auth: true }),
  );
  const profile = useCall(() => api(`/users/${Number(userId)}`));

  return (
    <div>
      <h1>내 정보</h1>

      <Section title="GET /users/me (인증 필요)">
        <button onClick={() => me.run()}>조회</button>
        <Result data={me.data} error={me.error} loading={me.loading} />
      </Section>

      <Section title="GET /users/me/dashboard (마이페이지 요약, 인증)">
        <button onClick={() => dashboard.run()}>요약 조회</button>
        <Result data={dashboard.data} error={dashboard.error} loading={dashboard.loading} />
      </Section>

      <Section title="PATCH /users/me (인증 필요)">
        <Field
          label="nickname"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
        />
        <Field
          label="profile_image (URL)"
          value={profileImage}
          onChange={(e) => setProfileImage(e.target.value)}
        />
        <Field
          label="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={() => update.run()}>수정</button>
        <Result data={update.data} error={update.error} loading={update.loading} />
      </Section>

      <Section title="DELETE /users/me (인증 필요, 계정 비활성화)">
        <button onClick={() => remove.run()}>탈퇴</button>
        <Result data={remove.data} error={remove.error} loading={remove.loading} />
      </Section>

      <Section title="GET /users/{id} (공개 프로필)">
        <Field
          label="user_id"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <button onClick={() => profile.run()}>조회</button>
        <Result data={profile.data} error={profile.error} loading={profile.loading} />
      </Section>
    </div>
  );
}
