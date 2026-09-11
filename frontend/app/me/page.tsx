"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Account" title="내 계정">
        <p>프로필 조회·수정, 마이페이지 활동 요약, 공개 프로필 확인.</p>
      </PageHeader>

      <Section title="내 정보" method="GET /users/me">
        <div className="actions">
          <button onClick={() => me.run()}>조회</button>
        </div>
        <Result {...me} />
      </Section>

      <Section title="마이페이지 요약" method="GET /users/me/dashboard">
        <div className="actions">
          <button onClick={() => dashboard.run()}>요약 조회</button>
        </div>
        <Result
          data={dashboard.data}
          error={dashboard.error}
          loading={dashboard.loading}
        />
      </Section>

      <Section title="정보 수정" method="PATCH /users/me">
        <Field
          label="닉네임"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
        />
        <Field
          label="프로필 이미지 (URL)"
          value={profileImage}
          onChange={(e) => setProfileImage(e.target.value)}
        />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => update.run()}>
            수정
          </button>
        </div>
        <Result {...update} />
      </Section>

      <Section title="회원 탈퇴" method="DELETE /users/me">
        <p className="hint">계정이 비활성화됩니다(소프트 삭제).</p>
        <div className="actions">
          <button onClick={() => remove.run()}>탈퇴</button>
        </div>
        <Result {...remove} />
      </Section>

      <Section title="공개 프로필" method="GET /users/{id}">
        <Field
          label="user_id"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => profile.run()}>조회</button>
        </div>
        <Result {...profile} />
      </Section>
    </div>
  );
}
