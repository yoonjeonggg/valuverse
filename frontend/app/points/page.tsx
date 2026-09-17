"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "../lib/api";
import { Card, PageHeader, useCall } from "../lib/ui";

type Mission = {
  key: string;
  description: string;
  reward: number;
  achieved: boolean;
  claimed: boolean;
};

type CouponCatalogRow = {
  key: string;
  cost: number;
  discount_percent: number;
  description: string;
};

type Coupon = {
  id: number;
  catalog_key: string;
  discount_percent: number;
  cost: number;
  is_used: boolean;
  expires_at: string;
};

const CHECKIN_STREAK_CAP = 7;

export default function PointsPage() {
  const [balance, setBalance] = useState<number | null>(null);
  const [streak, setStreak] = useState<number | null>(null);
  const [checkedInToday, setCheckedInToday] = useState(false);
  const [adToday, setAdToday] = useState<{ views: number; limit: number } | null>(null);
  const [liveMissions, setLiveMissions] = useState<Mission[] | null>(null);
  const [catalog, setCatalog] = useState<CouponCatalogRow[] | null>(null);
  const [ownedCoupons, setOwnedCoupons] = useState<Coupon[] | null>(null);

  const loadBalance = () =>
    api<{ balance: number }>("/users/me/points/balance", { auth: true })
      .then((r) => setBalance(r.balance))
      .catch(() => {});
  const loadCheckInStatus = () =>
    api<{ checked_in_today: boolean; streak: number }>("/points/check-in/status", { auth: true })
      .then((r) => {
        setCheckedInToday(r.checked_in_today);
        setStreak(r.streak);
      })
      .catch(() => {});
  const loadLiveMissions = () =>
    api<Mission[]>("/points/missions", { auth: true })
      .then(setLiveMissions)
      .catch(() => {});
  const loadOwnedCoupons = () =>
    api<Coupon[]>("/users/me/coupons", { auth: true })
      .then(setOwnedCoupons)
      .catch(() => {});

  useEffect(() => {
    api<CouponCatalogRow[]>("/points/coupons/catalog")
      .then(setCatalog)
      .catch(() => setCatalog([]));
    if (getToken()) {
      loadBalance();
      loadCheckInStatus();
      loadLiveMissions();
      loadOwnedCoupons();
    }
  }, []);

  const checkInCall = useCall(() =>
    api<{ streak: number; reward: number; balance: number }>("/points/check-in", {
      method: "POST",
      auth: true,
    }),
  );
  const submitCheckIn = async () => {
    const r = await checkInCall.run();
    if (r) {
      setStreak(r.streak);
      setBalance(r.balance);
      setCheckedInToday(true);
    }
  };

  const adCall = useCall(() =>
    api<{ views_today: number; daily_limit: number; balance: number }>("/points/ad-reward", {
      method: "POST",
      auth: true,
    }),
  );
  const submitAd = async () => {
    const r = await adCall.run();
    if (r) {
      setAdToday({ views: r.views_today, limit: r.daily_limit });
      setBalance(r.balance);
    }
  };

  const claimCall = useCall((key: string) =>
    api<{ balance: number }>(`/points/missions/${key}/claim`, { method: "POST", auth: true }),
  );
  const submitClaim = async (key: string) => {
    const r = await claimCall.run(key);
    if (r) {
      setBalance(r.balance);
      loadLiveMissions();
    }
  };

  const redeemCall = useCall((key: string) =>
    api(`/points/coupons/${key}/redeem`, { method: "POST", auth: true }),
  );
  const submitRedeem = async (key: string) => {
    const r = await redeemCall.run(key);
    if (r) {
      loadBalance();
      loadOwnedCoupons();
    }
  };

  const useCouponCall = useCall((id: number) =>
    api(`/points/coupons/${id}/use`, { method: "POST", auth: true }),
  );
  const submitUseCoupon = async (id: number) => {
    const r = await useCouponCall.run(id);
    if (r) loadOwnedCoupons();
  };

  return (
    <div>
      <PageHeader eyebrow="Economy" title="포인트">
        <p>
          포인트는 출석·미션·광고로만 적립되고, 예측 베팅·상단 노출권·수수료
          할인쿠폰에 소모됩니다. 현금 충전 경로는 없습니다.
        </p>
      </PageHeader>

      <Card
        title="출석 체크"
        right={balance !== null ? <span className="pointpill">{balance.toLocaleString()} P</span> : undefined}
      >
        <p className="hint">
          연속 출석 스트릭 — 매일 채워가면 보너스 포인트가 늘어납니다
          {streak ? ` (현재 ${streak}일 연속)` : ""}.
        </p>
        <div className="streak">
          {Array.from({ length: CHECKIN_STREAK_CAP }).map((_, i) => (
            <span key={i} className={"dot" + (streak !== null && i < streak ? " on" : "")}>
              {i + 1}일
            </span>
          ))}
        </div>
        <div className="actions">
          {checkedInToday ? (
            <span className="badge badge--ok">오늘 출석 완료</span>
          ) : (
            <button className="btn btn-primary" onClick={submitCheckIn} disabled={checkInCall.loading}>
              오늘 출석 체크
            </button>
          )}
        </div>
        {checkInCall.data && (
          <p className="hint">
            {checkInCall.data.streak}일 연속 출석 · {checkInCall.data.reward}P 적립
          </p>
        )}
        {checkInCall.error && <p className="hint hint--error">{checkInCall.error}</p>}
      </Card>

      <Card title="미션">
        {!liveMissions ? (
          <div className="empty">로그인하면 미션 진행 상황을 볼 수 있습니다.</div>
        ) : (
          <div className="missiongrid">
            {liveMissions.map((m) => (
              <div className="missionrow" key={m.key}>
                <span>
                  {m.description}
                  <span className="reward">+{m.reward}P</span>
                </span>
                {m.claimed ? (
                  <span className="badge badge--ok">수령완료</span>
                ) : m.achieved ? (
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => submitClaim(m.key)}
                    disabled={claimCall.loading}
                  >
                    받기
                  </button>
                ) : (
                  <span className="badge">미달성</span>
                )}
              </div>
            ))}
          </div>
        )}
        {claimCall.error && <p className="hint hint--error">{claimCall.error}</p>}
      </Card>

      <Card title="광고 보상">
        <p className="hint">
          하루 최대 {adToday?.limit ?? 5}회까지 시청할 때마다 포인트가 지급됩니다.
          {adToday && ` (오늘 ${adToday.views}/${adToday.limit}회 시청)`}
        </p>
        <div className="actions">
          <button className="btn btn-primary" onClick={submitAd} disabled={adCall.loading}>
            광고 시청하고 포인트 받기
          </button>
        </div>
        {adCall.error && <p className="hint hint--error">{adCall.error}</p>}
      </Card>

      <Card title="포인트 소모처 - 수수료 할인 쿠폰">
        {!catalog ? (
          <div className="empty">불러오는 중…</div>
        ) : (
          <div className="coupongrid">
            {catalog.map((c) => {
              const disabled = balance === null || balance < c.cost || redeemCall.loading;
              return (
                <div className="couponcard" key={c.key}>
                  <span className="pct">{c.discount_percent}% 할인</span>
                  <span className="cost">{c.cost.toLocaleString()}P</span>
                  <p className="hint">{c.description}</p>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => submitRedeem(c.key)}
                    disabled={disabled}
                  >
                    {balance === null ? "로그인 필요" : balance < c.cost ? "포인트 부족" : "교환하기"}
                  </button>
                </div>
              );
            })}
          </div>
        )}
        {redeemCall.error && <p className="hint hint--error">{redeemCall.error}</p>}

        <hr />
        <h3>내 쿠폰</h3>
        {!ownedCoupons || ownedCoupons.length === 0 ? (
          <div className="empty">보유한 쿠폰이 없습니다.</div>
        ) : (
          <ul className="bidlist">
            {ownedCoupons.map((c) => (
              <li key={c.id}>
                <span>
                  {c.discount_percent}% 할인 쿠폰
                  {c.is_used && " (사용됨)"}
                </span>
                {!c.is_used && (
                  <button
                    className="btn btn-sm"
                    onClick={() => submitUseCoupon(c.id)}
                    disabled={useCouponCall.loading}
                  >
                    사용
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        {useCouponCall.error && <p className="hint hint--error">{useCouponCall.error}</p>}
      </Card>
    </div>
  );
}
