"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [notificationId, setNotificationId] = useState("");

  const list = useCall(() =>
    api("/users/me/notifications", {
      auth: true,
      query: { unread: unreadOnly ? "true" : undefined },
    }),
  );
  const count = useCall(() =>
    api("/users/me/notifications/unread-count", { auth: true }),
  );
  const markRead = useCall(() =>
    api(`/notifications/${Number(notificationId)}/read`, {
      method: "POST",
      auth: true,
    }),
  );
  const readAll = useCall(() =>
    api("/notifications/read-all", { method: "POST", auth: true }),
  );

  return (
    <div>
      <h1>알림 (Notification)</h1>
      <p style={{ fontSize: 13 }}>
        입찰 경쟁·낙찰·스킬 정산·예측 정산·신고 처리 시 자동 생성됩니다.
      </p>

      <Section title="GET /users/me/notifications (인증)">
        <label style={{ display: "block", margin: "4px 0" }}>
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
          />{" "}
          안 읽은 것만 (unread=true)
        </label>
        <button onClick={() => list.run()}>목록 조회</button>
        <button onClick={() => count.run()}>안 읽은 개수</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
        <Result data={count.data} error={count.error} loading={count.loading} />
      </Section>

      <Section title="읽음 처리 (인증)">
        <Field
          label="notification_id"
          value={notificationId}
          onChange={(e) => setNotificationId(e.target.value)}
        />
        <button onClick={() => markRead.run()}>
          POST /notifications/{"{id}"}/read
        </button>
        <button onClick={() => readAll.run()}>POST /notifications/read-all</button>
        <Result data={markRead.data} error={markRead.error} loading={markRead.loading} />
        <Result data={readAll.data} error={readAll.error} loading={readAll.loading} />
      </Section>
    </div>
  );
}
