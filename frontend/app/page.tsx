"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, API_BASE_URL } from "./lib/api";
import { Icon } from "./lib/ui";

type Item = {
  id: number;
  title: string;
  category: string | null;
  current_price: number;
  auction_type: string;
  end_time: string;
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
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api("/health")
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
    api<Item[]>("/items", { query: { status: "ongoing", limit: 6 } })
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

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
            <Link key={it.id} href="/items" className="item-card">
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
