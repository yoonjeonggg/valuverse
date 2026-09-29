"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { announcePoints, api, getToken } from "../lib/api";
import type { Coupon, Mission } from "../lib/types";
import { Card, ErrorText, Icon, PageHeader, useCall } from "../lib/ui";

type Summary = {
  balance: number;
  checked_in_today: boolean;
  streak: number;
  streak_cap: number;
  next_check_in_reward: number;
  ad_views_today: number;
  ad_daily_limit: number;
  ad_reward: number;
  ad_next_available_at: string | null;
};

type CouponCatalogRow = {
  key: string;
  cost: number;
  discount_percent: number;
  description: string;
};

const MISSION_ICONS: Record<string, Parameters<typeof Icon>[0]["name"]> = {
  first_bid: "gavel",
  first_item: "box",
  first_review: "pen",
};

const isExpired = (c: Coupon) => new Date(c.expires_at).getTime() <= Date.now();

export default function PointsPage() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [catalog, setCatalog] = useState<CouponCatalogRow[] | null>(null);
  const [coupons, setCoupons] = useState<Coupon[] | null>(null);
  // 여러 행 중 어느 버튼이 처리 중인지 (나머지 행은 중복 요청만 막고 라벨은 그대로 둔다)
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    api<CouponCatalogRow[]>("/points/coupons/catalog")
      .then(setCatalog)
      .catch(() => setCatalog([]));
    // 잔액/출석/광고 상태는 요약 엔드포인트 하나로 받는다. 토큰이 없거나 만료됐으면 비로그인 상태.
    const token = getToken();
    (token
      ? api<Summary>("/users/me/points/summary", { auth: true })
      : Promise.reject(new Error("no token"))
    )
      .then((s) => {
        setSummary(s);
        setLoggedIn(true);
      })
      .catch(() => setLoggedIn(false));
    if (!token) return;
    api<Mission[]>("/points/missions", { auth: true })
      .then(setMissions)
      .catch(() => setMissions([]));
    api<Coupon[]>("/users/me/coupons", { auth: true })
      .then(setCoupons)
      .catch(() => setCoupons([]));
  }, []);

  // 광고 쿨다운 남은 초 (서버가 429 로 막기 전에 버튼을 미리 잠근다)
  const adAvailableAt = summary?.ad_next_available_at
    ? new Date(summary.ad_next_available_at).getTime()
    : null;
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (adAvailableAt === null) return;
    const id = setInterval(() => {
      const t = Date.now();
      setNowMs(t);
      if (t >= adAvailableAt) clearInterval(id);
    }, 1000);
    return () => clearInterval(id);
  }, [adAvailableAt]);
  const adCooldownSec =
    adAvailableAt !== null && adAvailableAt > nowMs ? Math.ceil((adAvailableAt - nowMs) / 1000) : 0;

  const patchSummary = (patch: Partial<Summary>) =>
    setSummary((s) => (s ? { ...s, ...patch } : s));

  // 이 화면에서 잔액이 바뀌면 헤더 잔액 표시에도 알린다.
  const balance = summary?.balance ?? null;
  useEffect(() => {
    if (balance !== null) announcePoints(balance);
  }, [balance]);

  const checkInCall = useCall(() =>
    api<{ streak: number; reward: number; balance: number; next_check_in_reward: number }>(
      "/points/check-in",
      {
        method: "POST",
        auth: true,
      },
    ),
  );
  const submitCheckIn = async () => {
    const r = await checkInCall.run();
    if (r)
      patchSummary({
        balance: r.balance,
        streak: r.streak,
        checked_in_today: true,
        next_check_in_reward: r.next_check_in_reward,
      });
  };

  const adCall = useCall(() =>
    api<{
      views_today: number;
      daily_limit: number;
      balance: number;
      next_available_at: string;
    }>("/points/ad-reward", {
      method: "POST",
      auth: true,
    }),
  );
  const submitAd = async () => {
    const r = await adCall.run();
    if (r) {
      setNowMs(Date.now());
      patchSummary({
        balance: r.balance,
        ad_views_today: r.views_today,
        ad_daily_limit: r.daily_limit,
        ad_next_available_at: r.next_available_at,
      });
    }
  };

  // 응답만으로 화면 상태를 갱신한다 (목록 전체를 다시 불러오지 않는다).
  const claimCall = useCall((key: string) =>
    api<{ key: string; balance: number }>(`/points/missions/${key}/claim`, {
      method: "POST",
      auth: true,
    }),
  );
  const submitClaim = async (key: string) => {
    setPending(`mission:${key}`);
    const r = await claimCall.run(key);
    setPending(null);
    if (r) {
      patchSummary({ balance: r.balance });
      setMissions((ms) => ms && ms.map((m) => (m.key === key ? { ...m, claimed: true } : m)));
    }
  };

  const redeemCall = useCall((key: string) =>
    api<Coupon>(`/points/coupons/${key}/redeem`, { method: "POST", auth: true }),
  );
  const submitRedeem = async (key: string) => {
    setPending(`redeem:${key}`);
    const r = await redeemCall.run(key);
    setPending(null);
    if (r) {
      setSummary((s) => (s ? { ...s, balance: s.balance - r.cost } : s));
      setCoupons((cs) => [r, ...(cs ?? [])]);
    }
  };

  const useCouponCall = useCall((id: number) =>
    api<Coupon>(`/points/coupons/${id}/use`, { method: "POST", auth: true }),
  );
  const submitUseCoupon = async (id: number) => {
    setPending(`use:${id}`);
    const r = await useCouponCall.run(id);
    setPending(null);
    if (r) setCoupons((cs) => cs && cs.map((c) => (c.id === id ? r : c)));
  };

  const streakCap = summary?.streak_cap ?? 7;
  const missionsDone = missions?.filter((m) => m.claimed).length ?? 0;
  const usableCoupons = coupons?.filter((c) => !c.is_used && !isExpired(c)).length ?? 0;
  const adLimitReached = !!summary && summary.ad_views_today >= summary.ad_daily_limit;

  return (
    <div>
      <PageHeader eyebrow="Economy" title="포인트">
        <p>
          포인트는 출석·미션·광고로만 적립되고, 예측 베팅·상단 노출권·수수료
          할인쿠폰에 소모됩니다. 현금 충전 경로는 없습니다.
        </p>
      </PageHeader>

      <section className="pointhero" aria-label="보유 포인트">
        <div className="pointhero__main">
          <span className="pointhero__label">
            <Icon name="coin" size={16} /> 보유 포인트
          </span>
          {loggedIn === false ? (
            <>
              <strong className="pointhero__balance">로그인이 필요합니다</strong>
              <Link href="/auth" className="btn pointhero__cta">
                로그인하고 포인트 모으기 <Icon name="arrow" size={14} />
              </Link>
            </>
          ) : (
            <strong className="pointhero__balance">
              {balance === null ? "-" : balance.toLocaleString()}
              <span>P</span>
            </strong>
          )}
        </div>
        {loggedIn !== false && (
          <dl className="pointhero__stats">
            <div>
              <dt>연속 출석</dt>
              <dd>{summary ? `${summary.streak}일` : "-"}</dd>
            </div>
            <div>
              <dt>미션 완료</dt>
              <dd>{missions ? `${missionsDone}/${missions.length}` : "-"}</dd>
            </div>
            <div>
              <dt>사용 가능 쿠폰</dt>
              <dd>{coupons ? `${usableCoupons}장` : "-"}</dd>
            </div>
          </dl>
        )}
      </section>

      <div className="pointgrid">
        <Card
          eyebrow="Daily"
          title="출석 체크"
          right={
            summary?.checked_in_today ? (
              <span className="statuschip statuschip--ok">
                <Icon name="check" size={14} /> 오늘 완료
              </span>
            ) : undefined
          }
        >
          <p className="hint">
            매일 이어서 출석하면 {streakCap}일차까지 보상이 커집니다. 하루라도 빠지면 1일차부터 다시 시작해요.
          </p>
          <ol className="streaktrack">
            {Array.from({ length: streakCap }, (_, i) => {
              const streak = summary?.streak ?? 0;
              const done = i < streak;
              const next = !summary?.checked_in_today && i === streak;
              return (
                <li key={i} className={done ? "is-done" : next ? "is-next" : undefined}>
                  <span className="streaktrack__mark">
                    {done ? <Icon name="check" size={16} /> : i + 1}
                  </span>
                  <span className="streaktrack__day">{i + 1}일</span>
                </li>
              );
            })}
          </ol>
          <div className="actions">
            {summary?.checked_in_today ? (
              <p className="hint">
                내일 출석하면 <b>+{summary.next_check_in_reward}P</b>
              </p>
            ) : (
              <button
                className="btn btn-primary btn-lg"
                onClick={submitCheckIn}
                disabled={!summary || checkInCall.loading}
              >
                <Icon name="calendar" size={16} />
                {checkInCall.loading
                  ? "처리 중…"
                  : `오늘 출석하고 +${summary?.next_check_in_reward ?? ""}P 받기`}
              </button>
            )}
          </div>
          {checkInCall.data && (
            <p className="notice notice--ok">
              <Icon name="check" size={14} /> {checkInCall.data.streak}일 연속 출석 ·{" "}
              {checkInCall.data.reward}P 적립
            </p>
          )}
          <ErrorText error={checkInCall.error} notice />
        </Card>

        <Card eyebrow="Reward" title="광고 보상">
          <p className="hint">
            광고 1회 시청마다 <b>+{summary?.ad_reward ?? 5}P</b>, 하루 최대{" "}
            {summary?.ad_daily_limit ?? 5}회까지 받을 수 있습니다.
          </p>
          {summary && (
            <div className="segbar" aria-label={`오늘 ${summary.ad_views_today}/${summary.ad_daily_limit}회 시청`}>
              {Array.from({ length: summary.ad_daily_limit }, (_, i) => (
                <span key={i} className={i < summary.ad_views_today ? "on" : undefined} />
              ))}
              <b>
                {summary.ad_views_today}/{summary.ad_daily_limit}
              </b>
            </div>
          )}
          <div className="actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={submitAd}
              disabled={!summary || adLimitReached || adCooldownSec > 0 || adCall.loading}
            >
              <Icon name={adCooldownSec > 0 ? "clock" : "play"} size={16} />
              {adLimitReached
                ? "오늘 한도를 모두 채웠어요"
                : adCall.loading
                  ? "처리 중…"
                  : adCooldownSec > 0
                    ? `${adCooldownSec}초 후 다시 받을 수 있어요`
                    : "광고 보고 포인트 받기"}
            </button>
          </div>
          <ErrorText error={adCall.error} notice />
        </Card>
      </div>

      <Card
        eyebrow="Mission"
        title="미션"
        right={missions && <span className="statuschip">{missionsDone}/{missions.length} 완료</span>}
      >
        {loggedIn === false ? (
          <div className="empty">로그인하면 미션 진행 상황을 볼 수 있습니다.</div>
        ) : !missions ? (
          <div className="empty">불러오는 중…</div>
        ) : (
          <ul className="missionlist">
            {missions.map((m) => {
              const state = m.claimed ? "claimed" : m.achieved ? "ready" : "locked";
              return (
                <li key={m.key} className={`missionlist__row is-${state}`}>
                  <span className="missionlist__icon">
                    <Icon name={MISSION_ICONS[m.key] ?? "target"} size={20} />
                  </span>
                  <span className="missionlist__text">
                    <b>{m.description}</b>
                    <span className="missionlist__reward">+{m.reward}P</span>
                  </span>
                  {state === "claimed" ? (
                    <span className="statuschip statuschip--ok">
                      <Icon name="check" size={14} /> 수령 완료
                    </span>
                  ) : state === "ready" ? (
                    <button
                      className="btn btn-primary"
                      onClick={() => submitClaim(m.key)}
                      disabled={pending !== null}
                    >
                      {pending === `mission:${m.key}` ? "처리 중…" : "보상 받기"}
                    </button>
                  ) : (
                    <span className="statuschip">
                      <Icon name="lock" size={14} /> 미달성
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <ErrorText error={claimCall.error} notice />
      </Card>

      <Card eyebrow="Spend" title="수수료 할인 쿠폰 교환">
        {!catalog ? (
          <div className="empty">불러오는 중…</div>
        ) : (
          <div className="ticketgrid">
            {catalog.map((c) => {
              const short = balance !== null && balance < c.cost;
              return (
                <div className="ticket" key={c.key}>
                  <div className="ticket__pct">
                    {c.discount_percent}
                    <span>%</span>
                  </div>
                  <div className="ticket__body">
                    <b>{c.description}</b>
                    <span className="ticket__cost">
                      <Icon name="coin" size={14} /> {c.cost.toLocaleString()}P
                    </span>
                    <button
                      className="btn btn-primary"
                      onClick={() => submitRedeem(c.key)}
                      disabled={balance === null || short || pending !== null}
                    >
                      {balance === null
                        ? "로그인 필요"
                        : short
                          ? `${(c.cost - balance).toLocaleString()}P 부족`
                          : pending === `redeem:${c.key}`
                            ? "처리 중…"
                            : "교환하기"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <ErrorText error={redeemCall.error} notice />
      </Card>

      <Card eyebrow="Wallet" title="내 쿠폰">
        {!coupons || coupons.length === 0 ? (
          <div className="empty">보유한 쿠폰이 없습니다.</div>
        ) : (
          <ul className="couponlist">
            {coupons.map((c) => {
              const expired = !c.is_used && isExpired(c);
              return (
                <li key={c.id} className={c.is_used || expired ? "is-off" : undefined}>
                  <span className="couponlist__icon">
                    <Icon name="ticket" size={20} />
                  </span>
                  <span className="couponlist__text">
                    <b>수수료 {c.discount_percent}% 할인</b>
                    <span>{new Date(c.expires_at).toLocaleDateString()}까지</span>
                  </span>
                  {c.is_used ? (
                    <span className="statuschip">사용됨</span>
                  ) : expired ? (
                    <span className="statuschip">기간 만료</span>
                  ) : (
                    <button
                      className="btn"
                      onClick={() => submitUseCoupon(c.id)}
                      disabled={pending !== null}
                    >
                      {pending === `use:${c.id}` ? "처리 중…" : "사용하기"}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <ErrorText error={useCouponCall.error} notice />
      </Card>
    </div>
  );
}
