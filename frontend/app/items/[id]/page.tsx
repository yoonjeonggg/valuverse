"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, API_BASE_URL, getToken } from "../../lib/api";
import { ChatWidget } from "../../lib/chat-widget";
import { Card, Countdown, Icon, useCall } from "../../lib/ui";

type Item = {
  id: number;
  seller_id: number;
  title: string;
  description: string | null;
  category: string | null;
  image_url: string | null;
  start_price: number;
  buy_now_price: number | null;
  current_price: number;
  auction_type: string;
  blind_price_rule: string;
  end_time: string;
  status: string;
  winner_id: number | null;
  final_price: number | null;
};

type Bid = {
  id: number;
  item_id: number;
  bidder_id: number;
  amount: number;
  is_cancelled: boolean;
  created_at: string;
};

type RankInfo = { item_id: number; my_bid_id: number; rank: number; total_bids: number };
type ResultRow = { id: number; bidder_id: number; amount: number; rank: number };

export default function ItemDetailPage() {
  const params = useParams<{ id: string }>();
  const itemId = Number(params.id);

  const [item, setItem] = useState<Item | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [meId, setMeId] = useState<number | null>(null);

  const [bidAmount, setBidAmount] = useState("");
  const bidCall = useCall(() =>
    api<Bid>(`/items/${itemId}/bids`, {
      method: "POST",
      auth: true,
      body: { amount: Number(bidAmount) },
    }),
  );
  const buyNowCall = useCall(() =>
    api(`/items/${itemId}/buy-now`, { method: "POST", auth: true }),
  );

  const [blindAmount, setBlindAmount] = useState("");
  const blindBidCall = useCall(() =>
    api(`/items/${itemId}/blind-bids`, {
      method: "POST",
      auth: true,
      body: { amount: Number(blindAmount) },
    }),
  );
  const [rank, setRank] = useState<RankInfo | null>(null);
  const [results, setResults] = useState<ResultRow[] | null>(null);

  useEffect(() => {
    api<Item>(`/items/${itemId}`)
      .then(setItem)
      .catch((e) => setLoadError(String(e)));
    const token = getToken();
    if (token) {
      api<{ id: number }>("/users/me", { auth: true })
        .then((u) => setMeId(u.id))
        .catch(() => {});
    }
  }, [itemId]);

  // 일반 경매: 입찰 이력 + 실시간 WebSocket 갱신
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    if (!item || item.auction_type !== "general") return;
    api<Bid[]>(`/items/${itemId}/bids`)
      .then(setBids)
      .catch(() => {});

    const base = API_BASE_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${base}/items/${itemId}/bid`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "bid") {
        setItem((prev) =>
          prev
            ? { ...prev, current_price: msg.current_price, end_time: msg.end_time }
            : prev,
        );
        setBids((prev) => [
          {
            id: msg.bid_id,
            item_id: msg.item_id,
            bidder_id: msg.bidder_id,
            amount: msg.amount,
            is_cancelled: false,
            created_at: new Date().toISOString(),
          },
          ...prev,
        ]);
      } else if (msg.type === "closed") {
        setItem((prev) =>
          prev
            ? { ...prev, status: msg.status, winner_id: msg.winner_id, final_price: msg.final_price }
            : prev,
        );
      }
    };
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.auction_type, itemId]);

  // 블라인드 경매: 내 순위(마감 전) / 전체 결과(마감 후)
  useEffect(() => {
    if (!item || item.auction_type !== "blind") return;
    if (item.status === "closed") {
      api<ResultRow[]>(`/items/${itemId}/blind-bids/results`)
        .then(setResults)
        .catch(() => {});
    } else if (getToken()) {
      api<RankInfo>(`/items/${itemId}/blind-bids/my-rank`, { auth: true })
        .then(setRank)
        .catch(() => setRank(null));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.status, item?.auction_type, itemId]);

  const submitBid = async () => {
    const res = await bidCall.run();
    if (res) setBidAmount("");
  };
  const submitBlindBid = async () => {
    const res = await blindBidCall.run();
    if (res) {
      setBlindAmount("");
      api<RankInfo>(`/items/${itemId}/blind-bids/my-rank`, { auth: true })
        .then(setRank)
        .catch(() => {});
    }
  };

  if (loadError) return <div className="empty">{loadError}</div>;
  if (!item) return <div className="empty">불러오는 중…</div>;

  const isBlind = item.auction_type === "blind";
  const isOwner = meId === item.seller_id;
  const isClosed = item.status === "closed";

  return (
    <div>
      <div className="detail-head">
        <div>
          <span className="cat">
            {isBlind ? "블라인드 경매" : "일반 경매"} · {item.category || "미분류"}
          </span>
          <h1>{item.title}</h1>
          <p className="seller">
            판매자 #{item.seller_id}
            {isOwner && " (나)"}
          </p>
        </div>
        <Countdown endTime={isClosed ? null : item.end_time} />
      </div>

      {item.description && <p>{item.description}</p>}

      {!isBlind && (
        <Card title="현재가">
          <div className="price-now">
            <span className="label">현재가</span>
            {item.current_price.toLocaleString()}원
          </div>
          {isClosed ? (
            <p className="hint">
              {item.winner_id
                ? `낙찰 완료 — 낙찰가 ${item.final_price?.toLocaleString()}원 (낙찰자 #${item.winner_id})`
                : "유찰되었습니다."}
            </p>
          ) : (
            <>
              <div className="row bidform">
                <input
                  type="number"
                  placeholder={`${item.current_price + 1}원 이상`}
                  value={bidAmount}
                  onChange={(e) => setBidAmount(e.target.value)}
                />
                <button
                  className="btn btn-primary"
                  onClick={submitBid}
                  disabled={bidCall.loading || isOwner || !bidAmount}
                >
                  입찰
                </button>
                {item.buy_now_price && (
                  <button
                    className="btn"
                    onClick={() => buyNowCall.run()}
                    disabled={buyNowCall.loading || isOwner}
                  >
                    즉시구매 ({item.buy_now_price.toLocaleString()}원)
                  </button>
                )}
              </div>
              {bidCall.error && <p className="hint hint--error">{bidCall.error}</p>}
              {buyNowCall.error && <p className="hint hint--error">{buyNowCall.error}</p>}
            </>
          )}
        </Card>
      )}

      {!isBlind && (
        <Card title="입찰 이력">
          {bids.length === 0 ? (
            <div className="empty">아직 입찰이 없습니다.</div>
          ) : (
            <ul className="bidlist">
              {bids.map((b) => (
                <li key={b.id} className={meId === b.bidder_id ? "mine" : undefined}>
                  <span>
                    입찰자 #{b.bidder_id}
                    {meId === b.bidder_id && " (나)"}
                  </span>
                  <span className="amt">{b.amount.toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {isBlind && !isClosed && (
        <Card title="비공개 입찰">
          <p className="hint">
            다른 참가자의 입찰가는 공개되지 않습니다. 마감 후 일괄 공개됩니다.
          </p>
          <div className="row bidform">
            <input
              type="number"
              placeholder="입찰가"
              value={blindAmount}
              onChange={(e) => setBlindAmount(e.target.value)}
            />
            <button
              className="btn btn-primary"
              onClick={submitBlindBid}
              disabled={blindBidCall.loading || isOwner || !blindAmount}
            >
              입찰
            </button>
          </div>
          {blindBidCall.error && <p className="hint hint--error">{blindBidCall.error}</p>}
          {rank && (
            <div className="rankcard">
              <div className="num">{rank.rank}위</div>
              <div className="of">전체 {rank.total_bids}명 중</div>
            </div>
          )}
        </Card>
      )}

      {isBlind && isClosed && (
        <Card title="공개 결과">
          {item.blind_price_rule === "second" && (
            <p className="hint">
              Vickrey(2nd-price) 방식 — 최고 입찰자가 2위 금액으로 낙찰됩니다.
            </p>
          )}
          {!results ? (
            <div className="empty">불러오는 중…</div>
          ) : (
            <ul className="bidlist">
              {results.map((r) => (
                <li key={r.id} className={meId === r.bidder_id ? "mine" : undefined}>
                  <span>
                    {r.rank}위 · 입찰자 #{r.bidder_id}
                    {meId === r.bidder_id && " (나)"}
                  </span>
                  <span className="amt">{r.amount.toLocaleString()}원</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <p>
        <Link href="/items" className="back-link">
          <Icon name="back" size={14} /> 목록으로
        </Link>
      </p>

      <ChatWidget itemId={item.id} itemType="item" />
    </div>
  );
}
