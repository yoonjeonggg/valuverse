"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, Field, PageHeader, Result, Section, useCall } from "../lib/ui";

type Me = {
  id: number;
  email: string;
  nickname: string;
  points: number;
  rating: number;
  created_at: string;
};

type Dashboard = {
  unread_notifications: number;
  attendance_streak: number;
  auction: { selling_ongoing: number; sold: number; won: number; active_bids: number };
  skill: { selling: number; bookings_in_progress: number; bookings_completed: number };
};

type Bid = {
  id: number;
  item_id: number;
  bidder_id: number;
  amount: number;
  is_cancelled: boolean;
  created_at: string;
};

type Item = {
  id: number;
  title: string;
  status: string;
  winner_id: number | null;
  final_price: number | null;
  current_price: number;
};

type Booking = {
  id: number;
  skill_item_id: number;
  seller_id: number;
  buyer_id: number;
  amount: number;
  scheduled_at: string;
  status: string;
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
  in_progress: "진행중",
  completed: "완료",
  no_show: "노쇼",
  cancelled: "취소",
};

const TABS = ["입찰중", "낙찰완료", "예약(스킬)", "포인트내역"] as const;
type Tab = (typeof TABS)[number];

function MyActivity() {
  const [myInfo, setMyInfo] = useState<Me | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [tab, setTab] = useState<Tab>("입찰중");

  const [bids, setBids] = useState<Bid[] | null>(null);
  const [items, setItems] = useState<Record<number, Item>>({});
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [txs, setTxs] = useState<PointTx[] | null>(null);

  useEffect(() => {
    api<Me>("/users/me", { auth: true }).then(setMyInfo).catch(() => {});
    api<Dashboard>("/users/me/dashboard", { auth: true }).then(setDash).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "입찰중" || tab === "낙찰완료") {
      api<Bid[]>("/users/me/bids", { auth: true }).then(async (list) => {
        setBids(list);
        const ids = Array.from(new Set(list.map((b) => b.item_id)));
        const fetched = await Promise.all(
          ids.map((id) => api<Item>(`/items/${id}`).catch(() => null)),
        );
        const map: Record<number, Item> = {};
        fetched.forEach((it) => {
          if (it) map[it.id] = it;
        });
        setItems(map);
      });
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

      <MyActivity />

      <Section title="내 정보 (API 콘솔)" method="GET /users/me">
        <div className="actions">
          <button onClick={() => me.run()}>조회</button>
        </div>
        <Result {...me} />
      </Section>

      <Section title="마이페이지 요약 (API 콘솔)" method="GET /users/me/dashboard">
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
