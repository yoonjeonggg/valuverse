"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function PointsPage() {
  const [amount, setAmount] = useState("1000");
  const [type, setType] = useState("admin");
  const [memo, setMemo] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [missionKey, setMissionKey] = useState("first_bid");
  const [couponKey, setCouponKey] = useState("fee_10");
  const [couponId, setCouponId] = useState("");

  const balance = useCall(() =>
    api("/users/me/points/balance", { auth: true }),
  );
  const checkIn = useCall(() =>
    api("/points/check-in", { method: "POST", auth: true }),
  );
  const missions = useCall(() => api("/points/missions", { auth: true }));
  const claimMission = useCall(() =>
    api(`/points/missions/${missionKey}/claim`, { method: "POST", auth: true }),
  );
  const adReward = useCall(() =>
    api("/points/ad-reward", { method: "POST", auth: true }),
  );
  const couponCatalog = useCall(() => api("/points/coupons/catalog"));
  const redeemCoupon = useCall(() =>
    api(`/points/coupons/${couponKey}/redeem`, { method: "POST", auth: true }),
  );
  const myCoupons = useCall(() => api("/users/me/coupons", { auth: true }));
  const useCoupon = useCall(() =>
    api(`/points/coupons/${Number(couponId)}/use`, { method: "POST", auth: true }),
  );
  const listTx = useCall(() =>
    api("/users/me/point-transactions", {
      auth: true,
      query: { type: typeFilter },
    }),
  );
  const createTx = useCall(() =>
    api("/point-transactions", {
      method: "POST",
      auth: true,
      body: {
        user_id: targetUserId ? Number(targetUserId) : undefined,
        amount: Number(amount),
        type,
        memo: memo || undefined,
      },
    }),
  );

  return (
    <div>
      <h1>포인트 (Point)</h1>

      <Section title="GET /users/me/points/balance (인증)">
        <button onClick={() => balance.run()}>잔액 조회</button>
        <Result data={balance.data} error={balance.error} loading={balance.loading} />
      </Section>

      <Section title="적립 — 출석 / 미션 / 광고 (인증)">
        <button onClick={() => checkIn.run()}>POST /points/check-in</button>
        <Result data={checkIn.data} error={checkIn.error} loading={checkIn.loading} />
        <button onClick={() => missions.run()}>GET /points/missions</button>
        <Result data={missions.data} error={missions.error} loading={missions.loading} />
        <Field
          label="mission key (first_bid/first_item/first_review)"
          value={missionKey}
          onChange={(e) => setMissionKey(e.target.value)}
        />
        <button onClick={() => claimMission.run()}>
          POST /points/missions/{"{key}"}/claim
        </button>
        <Result data={claimMission.data} error={claimMission.error} loading={claimMission.loading} />
        <button onClick={() => adReward.run()}>POST /points/ad-reward</button>
        <Result data={adReward.data} error={adReward.error} loading={adReward.loading} />
      </Section>

      <Section title="소모 — 수수료 할인 쿠폰 (FR-PRD-08)">
        <button onClick={() => couponCatalog.run()}>GET /points/coupons/catalog</button>
        <Result data={couponCatalog.data} error={couponCatalog.error} loading={couponCatalog.loading} />
        <Field
          label="catalog key (fee_5/fee_10/fee_20)"
          value={couponKey}
          onChange={(e) => setCouponKey(e.target.value)}
        />
        <button onClick={() => redeemCoupon.run()}>
          POST /points/coupons/{"{key}"}/redeem (인증)
        </button>
        <Result data={redeemCoupon.data} error={redeemCoupon.error} loading={redeemCoupon.loading} />
        <button onClick={() => myCoupons.run()}>GET /users/me/coupons (인증)</button>
        <Result data={myCoupons.data} error={myCoupons.error} loading={myCoupons.loading} />
        <Field
          label="coupon_id"
          value={couponId}
          onChange={(e) => setCouponId(e.target.value)}
        />
        <button onClick={() => useCoupon.run()}>
          POST /points/coupons/{"{id}"}/use (인증)
        </button>
        <Result data={useCoupon.data} error={useCoupon.error} loading={useCoupon.loading} />
      </Section>

      <Section title="POST /point-transactions (관리자 전용)">
        <p style={{ fontSize: 13 }}>
          일반 적립은 위의 출석/미션/광고를 사용하세요. 이 엔드포인트는 관리자 수동 조정용입니다.
        </p>
        <Field
          label="amount (양수=적립, 음수=차감)"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <Field label="type" value={type} onChange={(e) => setType(e.target.value)} />
        <Field label="memo" value={memo} onChange={(e) => setMemo(e.target.value)} />
        <Field
          label="user_id (생략 시 본인)"
          value={targetUserId}
          onChange={(e) => setTargetUserId(e.target.value)}
        />
        <button onClick={() => createTx.run()}>생성</button>
        <Result data={createTx.data} error={createTx.error} loading={createTx.loading} />
      </Section>

      <Section title="GET /users/me/point-transactions (인증)">
        <Field
          label="type 필터"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        />
        <button onClick={() => listTx.run()}>내역 조회</button>
        <Result data={listTx.data} error={listTx.error} loading={listTx.loading} />
      </Section>
    </div>
  );
}
