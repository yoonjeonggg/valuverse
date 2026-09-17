"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, PageHeader, useCall } from "../lib/ui";

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
  const [list, setList] = useState<Notification[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = (unread: boolean) =>
    api<Notification[]>("/users/me/notifications", { auth: true, query: { unread } })
      .then(setList)
      .catch((e) => setLoadError(String(e)));

  useEffect(() => {
    load(unreadOnly);
  }, [unreadOnly]);

  const markReadCall = useCall((id: number) =>
    api(`/notifications/${id}/read`, { method: "POST", auth: true }),
  );
  const markRead = async (id: number) => {
    const res = await markReadCall.run(id);
    if (res) load(unreadOnly);
  };

  const readAllCall = useCall(() =>
    api("/notifications/read-all", { method: "POST", auth: true }),
  );
  const markAllRead = async () => {
    const res = await readAllCall.run();
    if (res) load(unreadOnly);
  };

  return (
    <div>
      <PageHeader eyebrow="Activity" title="알림">
        <p>상위 입찰, 낙찰, 스킬 정산, 예측 정산, 신고 처리 등 이벤트가 발생하면 자동으로 쌓입니다.</p>
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
        {loadError ? (
          <div className="empty">{loadError}</div>
        ) : !list ? (
          <div className="empty">불러오는 중…</div>
        ) : list.length === 0 ? (
          <div className="empty">알림이 없습니다.</div>
        ) : (
          <ul className="notiflist">
            {list.map((n) => (
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
      </Card>
    </div>
  );
}
