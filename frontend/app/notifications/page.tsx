"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Activity" title="알림">
        <p>
          상위 입찰, 낙찰, 스킬 정산, 예측 정산, 신고 처리 등 이벤트가 발생하면
          자동으로 쌓입니다.
        </p>
      </PageHeader>

      <Section title="내 알림" method="GET /users/me/notifications">
        <label className="row" style={{ gap: 8 }}>
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
          />
          <span className="hint">안 읽은 것만 보기</span>
        </label>
        <div className="actions">
          <button className="btn-primary" onClick={() => list.run()}>
            목록 조회
          </button>
          <button onClick={() => count.run()}>안 읽은 개수</button>
        </div>
        <Result {...list} />
        <Result {...count} />
      </Section>

      <Section title="읽음 처리" method="POST /notifications/…">
        <Field
          label="notification_id"
          value={notificationId}
          onChange={(e) => setNotificationId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => markRead.run()}>이 알림 읽음</button>
          <button onClick={() => readAll.run()}>전체 읽음</button>
        </div>
        <Result {...markRead} />
        <Result {...readAll} />
      </Section>
    </div>
  );
}
