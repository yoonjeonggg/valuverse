"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, getToken } from "./lib/api";
import { AuctionCard, type AuctionCardItem, SkillCard, type SkillCardItem } from "./lib/cards";
import type { Item, Mission, SkillItem } from "./lib/types";
import { Icon } from "./lib/ui";

export const HOME_ITEMS_QUERY = { status: "ongoing", limit: 6 };
export const HOME_SKILL_ITEMS_QUERY = { status: "recruiting", limit: 4 };

function remaining(end: string): string {
  const ms = new Date(end).getTime() - Date.now();
  if (ms <= 0) return "마감";
  const h = Math.floor(ms / 3.6e6);
  if (h >= 24) return `${Math.floor(h / 24)}일 남음`;
  if (h >= 1) return `${h}시간 남음`;
  return `${Math.max(1, Math.floor(ms / 6e4))}분 남음`;
}

export function HomeView({
  initialItems,
  initialSkillItems,
}: {
  initialItems: AuctionCardItem[] | null;
  initialSkillItems: SkillCardItem[] | null;
}) {
  const [items, setItems] = useState<AuctionCardItem[] | null>(initialItems);
  const [skillItems, setSkillItems] = useState<SkillCardItem[] | null>(initialSkillItems);
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    // 서버에서 받아온 목록이 있으면 다시 부르지 않는다 (실패했을 때만 브라우저에서).
    if (!initialItems)
      api<Item[]>("/items", { query: HOME_ITEMS_QUERY })
        .then(setItems)
        .catch(() => setItems([]));
    if (!initialSkillItems)
      api<SkillItem[]>("/skill-items", { query: HOME_SKILL_ITEMS_QUERY })
        .then(setSkillItems)
        .catch(() => setSkillItems([]));
    const token = getToken();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoggedIn(!!token);
    if (token) {
      api<Mission[]>("/points/missions", { auth: true })
        .then(setMissions)
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const claimable = missions?.filter((m) => m.achieved && !m.claimed).length ?? 0;

  return (
    <div>
      <section className="hero">
        <h1>
          최고가만이 답은 아니다.
          <br />
          <span className="u">경매의 방식</span>을 고르세요.
        </h1>
        <p className="lead">
          실시간 경쟁 입찰, 심리전을 없앤 밀봉 입찰, 시간과 재능을 사고파는 스킬
          경매. 거래가 없는 날엔 포인트로 예측시장에 참여합니다.
        </p>
        <div className="row">
          <Link className="btn btn-primary" href="/items">
            경매 둘러보기
          </Link>
          {!loggedIn && (
            <Link className="btn" href="/auth">
              회원가입
            </Link>
          )}
        </div>
      </section>

      {claimable > 0 && (
        <div className="missionbanner">
          <span className="msg">
            출석·미션 보상 <b>{claimable}개</b>를 받을 수 있어요.
          </span>
          <Link className="btn btn-sm" href="/points">
            포인트 센터 <Icon name="arrow" size={14} />
          </Link>
        </div>
      )}

      <div className="section-label">
        <h2>지금 열려 있는 경매</h2>
        <Link href="/items">전체 보기</Link>
      </div>

      {items === null ? (
        <div className="empty">불러오는 중…</div>
      ) : items.length === 0 ? (
        <div className="empty">
          진행 중인 경매가 없습니다. <Link href="/items">경매를 등록</Link>해
          보세요.
        </div>
      ) : (
        <div className="item-grid">
          {items.map((it) => (
            <AuctionCard key={it.id} item={it} meta={remaining(it.end_time)} />
          ))}
        </div>
      )}

      <div className="section-label">
        <h2>지금 모집중인 스킬 경매</h2>
        <Link href="/skill-items">전체 보기</Link>
      </div>

      {skillItems === null ? (
        <div className="empty">불러오는 중…</div>
      ) : skillItems.length === 0 ? (
        <div className="empty">
          모집중인 스킬 상품이 없습니다.{" "}
          <Link href="/skill-items">스킬을 등록</Link>해 보세요.
        </div>
      ) : (
        <div className="item-grid">
          {skillItems.map((it) => (
            <SkillCard
              key={it.id}
              item={it}
              meta={it.duration_minutes ? `${it.duration_minutes}분` : "협의"}
            />
          ))}
        </div>
      )}
    </div>
  );
}
