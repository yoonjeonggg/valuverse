"use client";

import { useRef, useState } from "react";
import { api, API_BASE_URL, getToken } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

function toIso(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}

export default function ItemsPage() {
  // 목록 필터
  const [category, setCategory] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // 생성 폼
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [createCategory, setCreateCategory] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [startPrice, setStartPrice] = useState("1000");
  const [buyNowPrice, setBuyNowPrice] = useState("");
  const [auctionType, setAuctionType] = useState("general");
  const [blindPriceRule, setBlindPriceRule] = useState("first");
  const [endTime, setEndTime] = useState("");

  // 대상 아이템 / 입찰
  const [itemId, setItemId] = useState("");
  const [bidAmount, setBidAmount] = useState("");
  const [blindAmount, setBlindAmount] = useState("");
  const [bidId, setBidId] = useState("");
  const [blindBidId, setBlindBidId] = useState("");
  const [patchTitle, setPatchTitle] = useState("");

  const list = useCall(() =>
    api("/items", {
      query: { category, status: statusFilter },
    }),
  );
  const create = useCall(() =>
    api("/items", {
      method: "POST",
      auth: true,
      body: {
        title,
        description: description || undefined,
        category: createCategory || undefined,
        image_url: imageUrl || undefined,
        start_price: Number(startPrice),
        buy_now_price: buyNowPrice ? Number(buyNowPrice) : undefined,
        auction_type: auctionType || undefined,
        blind_price_rule: blindPriceRule || undefined,
        end_time: toIso(endTime),
      },
    }),
  );
  const getOne = useCall(() => api(`/items/${Number(itemId)}`));
  const patch = useCall(() =>
    api(`/items/${Number(itemId)}`, {
      method: "PATCH",
      auth: true,
      body: { title: patchTitle || undefined },
    }),
  );
  const del = useCall(() =>
    api(`/items/${Number(itemId)}`, { method: "DELETE", auth: true }),
  );
  const closeItem = useCall(() =>
    api(`/items/${Number(itemId)}/close`, { method: "POST", auth: true }),
  );
  const buyNow = useCall(() =>
    api(`/items/${Number(itemId)}/buy-now`, { method: "POST", auth: true }),
  );
  const spotlight = useCall(() =>
    api(`/items/${Number(itemId)}/spotlight`, { method: "POST", auth: true }),
  );

  const createBid = useCall(() =>
    api(`/items/${Number(itemId)}/bids`, {
      method: "POST",
      auth: true,
      body: { amount: Number(bidAmount) },
    }),
  );
  const listBids = useCall(() => api(`/items/${Number(itemId)}/bids`));
  const myBids = useCall(() => api("/users/me/bids", { auth: true }));
  const cancelBid = useCall(() =>
    api(`/bids/${Number(bidId)}`, { method: "DELETE", auth: true }),
  );

  const createBlind = useCall(() =>
    api(`/items/${Number(itemId)}/blind-bids`, {
      method: "POST",
      auth: true,
      body: { amount: Number(blindAmount) },
    }),
  );
  const myRank = useCall(() =>
    api(`/items/${Number(itemId)}/blind-bids/my-rank`, { auth: true }),
  );
  const blindResults = useCall(() =>
    api(`/items/${Number(itemId)}/blind-bids/results`),
  );
  const cancelBlind = useCall(() =>
    api(`/blind-bids/${Number(blindBidId)}`, { method: "DELETE", auth: true }),
  );

  // --- AI 보조 ---
  const [aiCategory, setAiCategory] = useState("");
  const [aiText, setAiText] = useState("");
  const priceSuggestion = useCall(() =>
    api("/ai/price-suggestion", { query: { category: aiCategory } }),
  );
  const abuseCheck = useCall(() =>
    api("/ai/abuse-check", { method: "POST", auth: true, body: { text: aiText } }),
  );

  // --- 실시간 입찰 WebSocket ---
  const wsRef = useRef<WebSocket | null>(null);
  const [wsLog, setWsLog] = useState<string[]>([]);
  const [wsAmount, setWsAmount] = useState("");
  const pushLog = (line: string) =>
    setWsLog((prev) => [`${new Date().toLocaleTimeString()}  ${line}`, ...prev].slice(0, 30));

  const wsConnect = () => {
    if (!itemId) return;
    wsRef.current?.close();
    const base = API_BASE_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${base}/items/${Number(itemId)}/bid`);
    wsRef.current = ws;
    ws.onopen = () => pushLog("연결됨");
    ws.onclose = () => pushLog("연결 종료");
    ws.onerror = () => pushLog("에러");
    ws.onmessage = (e) => pushLog(e.data);
  };
  const wsDisconnect = () => wsRef.current?.close();
  const wsSendBid = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return pushLog("먼저 연결하세요");
    ws.send(JSON.stringify({ token: getToken(), amount: Number(wsAmount) }));
  };

  return (
    <div>
      <h1>일반경매 (Item / Bid / Blind Bid)</h1>

      <Section title="GET /items">
        <Field
          label="category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
        <Field
          label="status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <button onClick={() => list.run()}>목록 조회</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="POST /items (인증 필요)">
        <Field label="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field
          label="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Field
          label="category"
          value={createCategory}
          onChange={(e) => setCreateCategory(e.target.value)}
        />
        <Field
          label="image_url"
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
        />
        <Field
          label="start_price"
          type="number"
          value={startPrice}
          onChange={(e) => setStartPrice(e.target.value)}
        />
        <Field
          label="buy_now_price"
          type="number"
          value={buyNowPrice}
          onChange={(e) => setBuyNowPrice(e.target.value)}
        />
        <Field
          label="auction_type (general/blind)"
          value={auctionType}
          onChange={(e) => setAuctionType(e.target.value)}
        />
        <Field
          label="blind_price_rule (first/second)"
          value={blindPriceRule}
          onChange={(e) => setBlindPriceRule(e.target.value)}
        />
        <Field
          label="end_time"
          type="datetime-local"
          value={endTime}
          onChange={(e) => setEndTime(e.target.value)}
        />
        <button onClick={() => create.run()}>등록</button>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="대상 아이템 ID">
        <Field
          label="item_id"
          value={itemId}
          onChange={(e) => setItemId(e.target.value)}
        />
        <div>
          <button onClick={() => getOne.run()}>GET /items/{"{id}"}</button>
          <button onClick={() => del.run()}>DELETE (인증)</button>
        </div>
        <Field
          label="patch title"
          value={patchTitle}
          onChange={(e) => setPatchTitle(e.target.value)}
        />
        <button onClick={() => patch.run()}>PATCH title (인증)</button>
        <Result data={getOne.data} error={getOne.error} loading={getOne.loading} />
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
        <Result data={del.data} error={del.error} loading={del.loading} />
      </Section>

      <Section title="낙찰 / 즉시구매 / 노출 — 위 item_id 사용">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button onClick={() => closeItem.run()}>
            POST /items/{"{id}"}/close (판매자)
          </button>
          <button onClick={() => buyNow.run()}>
            POST /items/{"{id}"}/buy-now (인증)
          </button>
          <button onClick={() => spotlight.run()}>
            POST /items/{"{id}"}/spotlight (포인트 차감)
          </button>
        </div>
        <Result data={closeItem.data} error={closeItem.error} loading={closeItem.loading} />
        <Result data={buyNow.data} error={buyNow.error} loading={buyNow.loading} />
        <Result data={spotlight.data} error={spotlight.error} loading={spotlight.loading} />
      </Section>

      <Section title="입찰 (Bid) — 위 item_id 사용">
        <Field
          label="amount"
          type="number"
          value={bidAmount}
          onChange={(e) => setBidAmount(e.target.value)}
        />
        <button onClick={() => createBid.run()}>POST /items/{"{id}"}/bids (인증)</button>
        <button onClick={() => listBids.run()}>GET /items/{"{id}"}/bids</button>
        <button onClick={() => myBids.run()}>GET /users/me/bids (인증)</button>
        <Result data={createBid.data} error={createBid.error} loading={createBid.loading} />
        <Result data={listBids.data} error={listBids.error} loading={listBids.loading} />
        <Result data={myBids.data} error={myBids.error} loading={myBids.loading} />
        <Field label="bid_id" value={bidId} onChange={(e) => setBidId(e.target.value)} />
        <button onClick={() => cancelBid.run()}>DELETE /bids/{"{id}"} (인증)</button>
        <Result data={cancelBid.data} error={cancelBid.error} loading={cancelBid.loading} />
      </Section>

      <Section title="블라인드 입찰 (Blind Bid) — 위 item_id 사용">
        <Field
          label="amount"
          type="number"
          value={blindAmount}
          onChange={(e) => setBlindAmount(e.target.value)}
        />
        <button onClick={() => createBlind.run()}>
          POST /items/{"{id}"}/blind-bids (인증)
        </button>
        <button onClick={() => myRank.run()}>my-rank (인증)</button>
        <button onClick={() => blindResults.run()}>results</button>
        <Result data={createBlind.data} error={createBlind.error} loading={createBlind.loading} />
        <Result data={myRank.data} error={myRank.error} loading={myRank.loading} />
        <Result data={blindResults.data} error={blindResults.error} loading={blindResults.loading} />
        <Field
          label="blind_bid_id"
          value={blindBidId}
          onChange={(e) => setBlindBidId(e.target.value)}
        />
        <button onClick={() => cancelBlind.run()}>
          DELETE /blind-bids/{"{id}"} (인증)
        </button>
        <Result data={cancelBlind.data} error={cancelBlind.error} loading={cancelBlind.loading} />
      </Section>

      <Section title="AI 보조 (통계·규칙 기반)">
        <Field
          label="category"
          value={aiCategory}
          onChange={(e) => setAiCategory(e.target.value)}
        />
        <button onClick={() => priceSuggestion.run()}>
          GET /ai/price-suggestion (시세 추천)
        </button>
        <Result data={priceSuggestion.data} error={priceSuggestion.error} loading={priceSuggestion.loading} />
        <Field
          label="text (설명 문구)"
          value={aiText}
          onChange={(e) => setAiText(e.target.value)}
        />
        <button onClick={() => abuseCheck.run()}>
          POST /ai/abuse-check (어뷰징 문구 탐지, 인증)
        </button>
        <Result data={abuseCheck.data} error={abuseCheck.error} loading={abuseCheck.loading} />
      </Section>

      <Section title="실시간 입찰 WS /items/{id}/bid — 위 item_id 사용">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button onClick={wsConnect}>연결</button>
          <button onClick={wsDisconnect}>끊기</button>
        </div>
        <Field
          label="amount"
          type="number"
          value={wsAmount}
          onChange={(e) => setWsAmount(e.target.value)}
        />
        <button onClick={wsSendBid}>WS 입찰 전송 (토큰 포함)</button>
        <pre
          style={{
            background: "#f4f4f4",
            color: "#111",
            padding: 8,
            marginTop: 8,
            maxHeight: 240,
            overflowY: "auto",
            fontSize: 12,
          }}
        >
          {wsLog.join("\n") || "(로그 없음)"}
        </pre>
      </Section>
    </div>
  );
}
