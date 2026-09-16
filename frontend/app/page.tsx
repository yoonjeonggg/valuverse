"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, API_BASE_URL, getToken } from "./lib/api";
import { Icon } from "./lib/ui";

type Item = {
  id: number;
  title: string;
  category: string | null;
  current_price: number;
  auction_type: string;
  end_time: string;
};

type SkillItem = {
  id: number;
  title: string;
  category: string | null;
  start_price: number;
  duration_minutes: number | null;
};

type Mission = {
  key: string;
  description: string;
  reward: number;
  achieved: boolean;
  claimed: boolean;
};

function remaining(end: string): string {
  const ms = new Date(end).getTime() - Date.now();
  if (ms <= 0) return "마감";
  const h = Math.floor(ms / 3.6e6);
  if (h >= 24) return `${Math.floor(h / 24)}일 남음`;
  if (h >= 1) return `${h}시간 남음`;
  return `${Math.max(1, Math.floor(ms / 6e4))}분 남음`;
}

export default function Home() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [skillItems, setSkillItems] = useState<SkillItem[] | null>(null);
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    api("/health")
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
    api<Item[]>("/items", { query: { status: "ongoing", limit: 6 } })
      .then(setItems)
      .catch(() => setItems([]));
    api<SkillItem[]>("/skill-items", { query: { status: "recruiting", limit: 4 } })
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
  }, []);

  const claimable = missions?.filter((m) => m.achieved && !m.claimed).length ?? 0;

  return (
    <div>
      <section className="hero">
        <div className="eyebrow">AI 경매 플랫폼</div>
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
          <Link className="btn" href="/auth">
            회원가입
          </Link>
        </div>
      </section>

      <div className="mechs">
        <article className="mech">
          <div className="ic">
            <Icon name="gavel" size={22} />
          </div>
          <h3>일반 경매</h3>
          <p>
            실시간으로 현재가가 오르고, 마감 직전 입찰은 자동으로 시간을
            연장합니다. 스나이핑이 통하지 않습니다.
          </p>
          <Link href="/items">
            바로가기 <Icon name="arrow" size={14} />
          </Link>
        </article>
        <article className="mech">
          <div className="ic">
            <Icon name="shield" size={22} />
          </div>
          <h3>블라인드 경매</h3>
          <p>
            남의 입찰가는 보이지 않고 내 순위만 보입니다. 마감 시 일괄 공개,
            1st-price 또는 Vickrey 방식으로 낙찰됩니다.
          </p>
          <Link href="/items">
            바로가기 <Icon name="arrow" size={14} />
          </Link>
        </article>
        <article className="mech">
          <div className="ic">
            <Icon name="clock" size={22} />
          </div>
          <h3>스킬 경매</h3>
          <p>
            과외 2시간, 로고 디자인 같은 무형 자산을 거래합니다. 낙찰금은
            에스크로에 보관됐다가 서비스 완료 후 정산됩니다.
          </p>
          <Link href="/skill-items">
            바로가기 <Icon name="arrow" size={14} />
          </Link>
        </article>
      </div>

      <div className="missionbanner">
        <span className="msg">
          {loggedIn ? (
            claimable > 0 ? (
              <>
                오늘의 출석·미션 중 <b>{claimable}개</b> 보상을 받을 수 있어요.
              </>
            ) : (
              "오늘의 출석 체크와 미션을 확인해 보세요."
            )
          ) : (
            "로그인하면 출석·미션·광고 시청으로 포인트를 모을 수 있어요."
          )}
        </span>
        <Link className="btn btn-sm" href="/points">
          포인트 센터 가기 <Icon name="arrow" size={14} />
        </Link>
      </div>

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
            <Link key={it.id} href={`/items/${it.id}`} className="item-card">
              <span className="cat">
                {it.auction_type === "blind" ? "블라인드" : "일반"} ·{" "}
                {it.category || "미분류"}
              </span>
              <span className="ttl">{it.title}</span>
              <span className="price">
                {it.current_price.toLocaleString()}원
              </span>
              <span className="meta">{remaining(it.end_time)}</span>
            </Link>
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
            <Link key={it.id} href={`/skill-items/${it.id}`} className="item-card">
              <span className="cat">{it.category || "미분류"}</span>
              <span className="ttl">{it.title}</span>
              <span className="price">{it.start_price.toLocaleString()}원</span>
              <span className="meta">
                {it.duration_minutes ? `${it.duration_minutes}분` : "협의"}
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="statusline">
        <span className={"dot" + (online === false ? " bad" : "")} />
        {online === null
          ? "백엔드 상태 확인 중…"
          : online
            ? `백엔드 연결됨 — ${API_BASE_URL}`
            : `백엔드에 연결할 수 없습니다 — ${API_BASE_URL}`}
      </div>
    </div>
  );
}
