"use client";

import { useState } from "react";
import { api, apiPost } from "../lib/api";
import { Card, Loadable, PageHeader, useCall, useLoad } from "../lib/ui";

type Notification = {
  id: number;
  type: string;
  message: string;
  related_type: string | null;
  related_id: number | null;
  is_read: boolean;
  created_at: string;
};

export default function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const list = useLoad(
    () =>
      api<Notification[]>("/users/me/notifications", {
        auth: true,
        query: { unread: unreadOnly },
      }),
    [unreadOnly],
  );

  const markReadCall = useCall((id: number) => apiPost(`/notifications/${id}/read`));
  const markRead = async (id: number) => {
    const res = await markReadCall.run(id);
    if (res) list.reload();
  };

  const readAllCall = useCall(() => apiPost("/notifications/read-all"));
  const markAllRead = async () => {
    const res = await readAllCall.run();
    if (res) list.reload();
  };

  return (
    <div>
      <PageHeader title="알림">
        <p>
          상위 입찰, 낙찰, 스킬 정산, 예측 정산, 신고 처리 등 이벤트가 발생하면 자동으로 쌓입니다.
        </p>
      </PageHeader>

      <Card
        title="내 알림"
        right={
          <div className="row" style={{ gap: 8 }}>
            <label className="row" style={{ gap: 6 }}>
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => setUnreadOnly(e.target.checked)}
              />
              <span className="hint" style={{ margin: 0 }}>
                안 읽은 것만
              </span>
            </label>
            <button className="btn-sm" onClick={markAllRead} disabled={readAllCall.loading}>
              모두 읽음
            </button>
          </div>
        }
      >
        <Loadable
          data={list.data}
          error={list.error}
          onRetry={list.reload}
          empty="알림이 없습니다."
        >
          {(rows) => (
            <ul className="notiflist">
              {rows.map((n) => (
                <li key={n.id} className={n.is_read ? undefined : "unread"}>
                  <span className="msg">{n.message}</span>
                  <span className="meta">
                    {new Date(n.created_at).toLocaleString()}
                    {!n.is_read && (
                      <button
                        className="btn-sm"
                        onClick={() => markRead(n.id)}
                        disabled={markReadCall.loading}
                      >
                        읽음
                      </button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Loadable>
      </Card>
    </div>
  );
}
