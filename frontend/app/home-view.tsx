"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, getToken } from "./lib/api";
import { AuctionCard, type AuctionCardItem, SkillCard, type SkillCardItem } from "./lib/cards";
import type { Item, Mission, SkillItem } from "./lib/types";
import { Icon, Loadable, useLoad } from "./lib/ui";

export const HOME_ITEMS_QUERY = { status: "ongoing", limit: 6 };
export const HOME_SKILL_ITEMS_QUERY = { status: "recruiting", limit: 4 };

const MODES: [href: string, name: string, desc: string][] = [
  ["/items", "일반 경매", "공개 입찰, 마감 직전 입찰 시 자동 연장"],
  ["/items", "블라인드 경매", "밀봉 입찰 후 마감 때 일괄 공개"],
  ["/skill-items", "스킬 경매", "시간과 재능을 사고파는 예약형 경매"],
  ["/predictions", "예측시장", "포인트로 결과를 맞히는 시장"],
];

function remaining(end: string): string {
  const ms = new Date(end).getTime() - Date.now();
  if (ms <= 0) return "마감";
  const h = Math.floor(ms / 3.6e6);
  if (h >= 24 * 365) return `${new Date(end).toLocaleDateString("ko-KR")} 마감`;
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
  // 서버에서 받아온 목록이 있으면 다시 부르지 않는다 (실패했을 때만 브라우저에서).
  const items = useLoad<AuctionCardItem[]>(
    () => api<Item[]>("/items", { query: HOME_ITEMS_QUERY }),
    [],
    { initial: initialItems },
  );
  const skillItems = useLoad<SkillCardItem[]>(
    () => api<SkillItem[]>("/skill-items", { query: HOME_SKILL_ITEMS_QUERY }),
    [],
    { initial: initialSkillItems },
  );
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    const token = getToken();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoggedIn(!!token);
    if (token) {
      api<Mission[]>("/points/missions", { auth: true })
        .then(setMissions)
        .catch(() => {});
    }
  }, []);

  const claimable = missions?.filter((m) => m.achieved && !m.claimed).length ?? 0;

  // 마감이 가까운 순으로 몇 개만 오른쪽 보드에 올린다.
  const endingSoon = items.data
    ? [...items.data]
        .sort((a, b) => new Date(a.end_time).getTime() - new Date(b.end_time).getTime())
        .slice(0, 5)
    : null;

  return (
    <div>
      <div className="home-top">
        <section className="hero">
          <h1>
            최고가만이 답은 아니다.
            <br />
            <span className="u">경매의 방식</span>을 고르세요.
          </h1>
          <p className="lead">
            실시간 경쟁 입찰, 심리전을 없앤 밀봉 입찰, 시간과 재능을 사고파는 스킬 경매. 거래가 없는
            날엔 포인트로 예측시장에 참여합니다.
          </p>
          <div className="row">
            <Link className="btn btn-primary btn-lg" href="/items">
              경매 둘러보기
            </Link>
            {!loggedIn && (
              <Link className="btn btn-lg" href="/auth">
                회원가입
              </Link>
            )}
          </div>

          <ul className="modes">
            {MODES.map(([href, name, desc]) => (
              <li key={name}>
                <Link href={href}>
                  <span className="modes__name">{name}</span>
                  <span className="modes__desc">{desc}</span>
                  <Icon name="arrow" size={16} />
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <aside className="board" aria-label="마감 임박 경매">
          <div className="board__head">
            <h2>마감 임박</h2>
            <Link href="/items">전체</Link>
          </div>
          <Loadable
            data={endingSoon}
            error={items.error}
            onRetry={items.reload}
            empty="진행 중인 경매가 없습니다."
          >
            {(list) => (
              <ol>
                {list.map((it, i) => {
                  const left = remaining(it.end_time);
                  const urgent = new Date(it.end_time).getTime() - Date.now() < 3.6e6;
                  return (
                    <li key={it.id}>
                      <Link href={`/items/${it.id}`}>
                        <span className="board__no">{i + 1}</span>
                        <span className="board__ttl">{it.title}</span>
                        <span className="board__price">
                          {it.current_price.toLocaleString()}원
                        </span>
                        <span className="board__sub">
                          {it.auction_type === "blind" ? "블라인드" : "일반"} ·{" "}
                          {it.category || "미분류"}
                        </span>
                        <span
                          className={"board__left" + (urgent ? " urgent" : "")}
                          suppressHydrationWarning
                        >
                          {left}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ol>
            )}
          </Loadable>
        </aside>
      </div>

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
        <h2>진행 중인 경매</h2>
        <Link href="/items">전체 보기</Link>
      </div>

      <Loadable
        data={items.data}
        error={items.error}
        onRetry={items.reload}
        empty={
          <>
            진행 중인 경매가 없습니다. <Link href="/items">경매를 등록</Link>해 보세요.
          </>
        }
      >
        {(list) => (
          <div className="item-grid">
            {list.map((it) => (
              <AuctionCard key={it.id} item={it} meta={remaining(it.end_time)} />
            ))}
          </div>
        )}
      </Loadable>

      <div className="section-label">
        <h2>모집 중인 스킬</h2>
        <Link href="/skill-items">전체 보기</Link>
      </div>

      <Loadable
        data={skillItems.data}
        error={skillItems.error}
        onRetry={skillItems.reload}
        empty={
          <>
            모집중인 스킬 상품이 없습니다. <Link href="/skill-items">스킬을 등록</Link>해 보세요.
          </>
        }
      >
        {(list) => (
          <div className="item-grid">
            {list.map((it) => (
              <SkillCard
                key={it.id}
                item={it}
                meta={it.duration_minutes ? `${it.duration_minutes}분` : "협의"}
              />
            ))}
          </div>
        )}
      </Loadable>
    </div>
  );
}
