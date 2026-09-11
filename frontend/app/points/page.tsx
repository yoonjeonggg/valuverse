"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Economy" title="포인트">
        <p>
          포인트는 출석·미션·광고로만 적립되고, 예측 베팅·상단 노출권·수수료
          할인쿠폰에 소모됩니다. 현금 충전 경로는 없습니다.
        </p>
      </PageHeader>

      <Section title="잔액" method="GET /users/me/points/balance">
        <div className="actions">
          <button onClick={() => balance.run()}>잔액 조회</button>
        </div>
        <Result {...balance} />
      </Section>

      <Section title="적립 — 출석 · 미션 · 광고" method="POST /points/…">
        <div className="actions">
          <button className="btn-primary" onClick={() => checkIn.run()}>
            출석 체크
          </button>
          <button onClick={() => adReward.run()}>광고 보상</button>
          <button onClick={() => missions.run()}>미션 목록</button>
        </div>
        <Result {...checkIn} />
        <Result {...adReward} />
        <Result {...missions} />
        <Field
          label="미션 key (first_bid/first_item/first_review)"
          value={missionKey}
          onChange={(e) => setMissionKey(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => claimMission.run()}>미션 보상 수령</button>
        </div>
        <Result
          data={claimMission.data}
          error={claimMission.error}
          loading={claimMission.loading}
        />
      </Section>

      <Section title="소모 — 수수료 할인 쿠폰" method="POST /points/coupons/…">
        <div className="actions">
          <button onClick={() => couponCatalog.run()}>쿠폰 카탈로그</button>
        </div>
        <Result
          data={couponCatalog.data}
          error={couponCatalog.error}
          loading={couponCatalog.loading}
        />
        <Field
          label="카탈로그 key (fee_5/fee_10/fee_20)"
          value={couponKey}
          onChange={(e) => setCouponKey(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => redeemCoupon.run()}>
            포인트로 교환
          </button>
          <button onClick={() => myCoupons.run()}>내 쿠폰</button>
        </div>
        <Result
          data={redeemCoupon.data}
          error={redeemCoupon.error}
          loading={redeemCoupon.loading}
        />
        <Result {...myCoupons} />
        <Field
          label="coupon_id"
          value={couponId}
          onChange={(e) => setCouponId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => useCoupon.run()}>쿠폰 사용</button>
        </div>
        <Result {...useCoupon} />
      </Section>

      <Section title="포인트 내역" method="GET /users/me/point-transactions">
        <Field
          label="type 필터"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => listTx.run()}>내역 조회</button>
        </div>
        <Result {...listTx} />
      </Section>

      <Section title="수동 조정" method="POST /point-transactions · 관리자">
        <p className="hint">
          일반 적립은 위의 출석·미션·광고를 사용하세요. 이 엔드포인트는 관리자
          수동 조정용입니다.
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
        <div className="actions">
          <button onClick={() => createTx.run()}>생성</button>
        </div>
        <Result {...createTx} />
      </Section>
    </div>
  );
}
