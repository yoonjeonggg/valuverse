"use client";

import { useEffect, useState } from "react";
import { api, apiDelete, apiPatch, setToken } from "../lib/api";
import { useMe } from "../lib/me";
import type { Bid, Booking, Item } from "../lib/types";
import { Card, ErrorText, Field, PageHeader, useCall } from "../lib/ui";

type Dashboard = {
  unread_notifications: number;
  attendance_streak: number;
  auction: { selling_ongoing: number; sold: number; won: number; active_bids: number };
  skill: { selling: number; bookings_in_progress: number; bookings_completed: number };
};

type PointTx = {
  id: number;
  amount: number;
  type: string;
  memo: string | null;
  balance_after: number;
  created_at: string;
};

const BOOKING_STATUS_LABEL: Record<string, string> = {
  pending: "수락 대기",
  in_progress: "진행중",
  completed: "완료",
  no_show: "노쇼",
  cancelled: "취소",
};

const TABS = ["입찰중", "낙찰완료", "예약(스킬)", "포인트내역"] as const;
type Tab = (typeof TABS)[number];

function MyActivity() {
  const myInfo = useMe();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [tab, setTab] = useState<Tab>("입찰중");

  const [bids, setBids] = useState<Bid[] | null>(null);
  const [items, setItems] = useState<Record<number, Item>>({});
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [txs, setTxs] = useState<PointTx[] | null>(null);

  useEffect(() => {
    api<Dashboard>("/users/me/dashboard", { auth: true }).then(setDash).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "입찰중" || tab === "낙찰완료") {
      api<Bid[]>("/users/me/bids", { auth: true })
        .then(async (list) => {
          setBids(list);
          // 입찰한 상품들을 상품마다 요청하지 않고 한 번에 가져온다.
          const ids = Array.from(new Set(list.map((b) => b.item_id)));
          const fetched = ids.length
            ? await api<Item[]>("/items", { query: { ids, limit: 200 } })
            : [];
          setItems(Object.fromEntries(fetched.map((it) => [it.id, it])));
        })
        .catch(() => setBids([]));
    } else if (tab === "예약(스킬)") {
      api<Booking[]>("/skill-bookings", { auth: true }).then(setBookings).catch(() => {});
    } else if (tab === "포인트내역") {
      api<PointTx[]>("/users/me/point-transactions", { auth: true }).then(setTxs).catch(() => {});
    }
  }, [tab]);

  const activeBids =
    bids?.filter((b) => !b.is_cancelled && items[b.item_id]?.status === "ongoing") ?? [];
  const wonItems = Object.values(items).filter((it) => myInfo && it.winner_id === myInfo.id);

  return (
    <>
      {myInfo && (
        <p className="hint">
          {myInfo.nickname} ({myInfo.email}) · 평점 {myInfo.rating.toFixed(1)} · 가입일{" "}
          {new Date(myInfo.created_at).toLocaleDateString()}
        </p>
      )}
      {dash && (
        <div className="statrow">
          <div className="stat">
            <div className="num">{myInfo?.points.toLocaleString() ?? "-"}</div>
            <div className="lbl">보유 포인트</div>
          </div>
          <div className="stat">
            <div className="num">{dash.auction.active_bids}</div>
            <div className="lbl">입찰중 상품</div>
          </div>
          <div className="stat">
            <div className="num">{dash.auction.won}</div>
            <div className="lbl">낙찰 완료</div>
          </div>
          <div className="stat">
            <div className="num">{dash.skill.bookings_in_progress}</div>
            <div className="lbl">스킬 예약 진행중</div>
          </div>
          <div className="stat">
            <div className="num">{dash.attendance_streak}</div>
            <div className="lbl">출석 스트릭</div>
          </div>
          <div className="stat">
            <div className="num">{dash.unread_notifications}</div>
            <div className="lbl">안읽은 알림</div>
          </div>
        </div>
      )}

      <Card>
        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : undefined}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "입찰중" &&
          (activeBids.length === 0 ? (
            <div className="empty">진행중인 경매에 입찰한 내역이 없습니다. (일반 경매 기준)</div>
          ) : (
            <ul className="bidlist">
              {activeBids.map((b) => (
                <li key={b.id}>
                  <span>{items[b.item_id]?.title ?? `상품 #${b.item_id}`}</span>
                  <span className="amt">{b.amount.toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          ))}

        {tab === "낙찰완료" &&
          (wonItems.length === 0 ? (
            <div className="empty">낙찰받은 상품이 없습니다. (일반 경매 기준)</div>
          ) : (
            <ul className="bidlist">
              {wonItems.map((it) => (
                <li key={it.id}>
                  <span>{it.title}</span>
                  <span className="amt">{(it.final_price ?? it.current_price).toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          ))}

        {tab === "예약(스킬)" &&
          (!bookings || bookings.length === 0 ? (
            <div className="empty">스킬 예약 내역이 없습니다.</div>
          ) : (
            <ul className="bidlist">
              {bookings.map((b) => (
                <li key={b.id}>
                  <span>
                    스킬 상품 #{b.skill_item_id} · {new Date(b.scheduled_at).toLocaleDateString()}
                    {(b.status === "no_show" || b.status === "cancelled") && (
                      <span className="badge badge--warn" style={{ marginLeft: 8 }}>
                        {BOOKING_STATUS_LABEL[b.status]}
                      </span>
                    )}
                  </span>
                  <span className="amt">{b.amount.toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          ))}

        {tab === "포인트내역" &&
          (!txs || txs.length === 0 ? (
            <div className="empty">포인트 내역이 없습니다.</div>
          ) : (
            <ul className="txlist">
              {txs.map((t) => (
                <li key={t.id}>
                  <span className="memo">
                    {t.memo || t.type}
                    <span className="time">{new Date(t.created_at).toLocaleString()}</span>
                  </span>
                  <span className={"amt " + (t.amount >= 0 ? "pos" : "neg")}>
                    {t.amount >= 0 ? "+" : ""}
                    {t.amount.toLocaleString()}P
                  </span>
                </li>
              ))}
            </ul>
          ))}
      </Card>
    </>
  );
}

export default function MePage() {
  const [nickname, setNickname] = useState("");
  const [profileImage, setProfileImage] = useState("");
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");

  const update = useCall(() =>
    apiPatch("/users/me", {
      nickname: nickname || undefined,
      profile_image: profileImage || undefined,
      password: password || undefined,
      // 비밀번호를 바꿀 때만 현재 비밀번호를 함께 보낸다 (서버가 확인)
      current_password: password ? currentPassword : undefined,
    }),
  );
  const submitUpdate = async () => {
    const res = await update.run();
    if (res) {
      setNickname("");
      setProfileImage("");
      setPassword("");
      setCurrentPassword("");
    }
  };

  // 탈퇴는 되돌릴 수 없으므로 한 번 더 확인받고, 끝나면 토큰을 지우고 홈으로 보낸다.
  const [confirmRemove, setConfirmRemove] = useState(false);
  const remove = useCall(() => apiDelete("/users/me"));
  const submitRemove = async () => {
    const res = await remove.run();
    if (res !== undefined) {
      setToken(null);
      // 헤더(잔액/알림)가 마운트 시점의 토큰으로 그려지므로 클라이언트 이동 대신 새로 불러온다.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/";
    }
  };

  return (
    <div>
      <PageHeader title="내 계정">
        <p>활동 요약과 입찰/낙찰/예약/포인트 내역을 확인하고, 프로필을 관리합니다.</p>
      </PageHeader>

      <MyActivity />

      <Card title="정보 수정">
        <Field
          label="닉네임"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="변경할 닉네임"
          autoComplete="nickname"
        />
        <Field
          label="프로필 이미지 URL"
          value={profileImage}
          onChange={(e) => setProfileImage(e.target.value)}
          placeholder="https://…"
          type="url"
          autoComplete="off"
        />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="변경할 비밀번호"
          autoComplete="new-password"
        />
        {password && (
          <Field
            label="현재 비밀번호"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="본인 확인을 위해 입력"
            autoComplete="current-password"
          />
        )}
        <div className="actions">
          <button className="btn btn-primary" onClick={submitUpdate} disabled={update.loading}>
            수정
          </button>
        </div>
        <ErrorText error={update.error} />
      </Card>

      <Card title="회원 탈퇴">
        <p className="hint">탈퇴 시 계정이 비활성화됩니다.</p>
        <div className="actions">
          {confirmRemove ? (
            <>
              <span className="hint">정말 탈퇴할까요?</span>
              <button className="btn btn-danger" onClick={submitRemove} disabled={remove.loading}>
                탈퇴 확정
              </button>
              <button onClick={() => setConfirmRemove(false)} disabled={remove.loading}>
                취소
              </button>
            </>
          ) : (
            <button onClick={() => setConfirmRemove(true)}>탈퇴</button>
          )}
        </div>
        <ErrorText error={remove.error} />
      </Card>
    </div>
  );
}
