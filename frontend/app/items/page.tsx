"use client";

import { useRef, useState } from "react";
import { api, API_BASE_URL, getToken } from "../lib/api";
import { toIso } from "../lib/format";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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

  const descSuggestion = useCall(() =>
    api<{ draft_description: string; suggestions: string[] }>("/ai/description-suggestion", {
      method: "POST",
      auth: true,
      body: {
        title,
        category: createCategory || undefined,
        existing_description: description || undefined,
      },
    }),
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
      <PageHeader eyebrow="Auction" title="일반 · 블라인드 경매">
        <p>
          공개 실시간 입찰과 밀봉 입찰을 한 화면에서 다룹니다. 상품 등록 시
          auction_type 으로 방식을, blind_price_rule 로 낙찰 규칙을 정합니다.
        </p>
      </PageHeader>

      <Section title="상품 목록" method="GET /items">
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
        <div className="actions">
          <button onClick={() => list.run()}>목록 조회</button>
        </div>
        <Result {...list} />
      </Section>

      <Section title="상품 등록" method="POST /items">
        <Field label="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field
          label="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => descSuggestion.run()} disabled={!title || descSuggestion.loading}>
            AI 설명 제안 받기
          </button>
        </div>
        {descSuggestion.data && (
          <div className="card" style={{ margin: 0 }}>
            <p className="hint">{descSuggestion.data.draft_description}</p>
            <div className="actions">
              <button
                className="btn-sm"
                onClick={() => setDescription(descSuggestion.data!.draft_description)}
              >
                이 초안 적용
              </button>
            </div>
            {descSuggestion.data.suggestions.length > 0 && (
              <ul className="hint" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                {descSuggestion.data.suggestions.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            )}
          </div>
        )}
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
        <div className="actions">
          <button className="btn-primary" onClick={() => create.run()}>
            등록
          </button>
        </div>
        <Result {...create} />
      </Section>

      <Section title="대상 상품 선택" method="GET · PATCH · DELETE /items/{id}">
        <Field
          label="item_id"
          value={itemId}
          onChange={(e) => setItemId(e.target.value)}
        />
        <Field
          label="patch title"
          value={patchTitle}
          onChange={(e) => setPatchTitle(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => getOne.run()}>조회</button>
          <button onClick={() => patch.run()}>제목 수정</button>
          <button onClick={() => del.run()}>삭제</button>
        </div>
        <Result {...getOne} />
        <Result {...patch} />
        <Result {...del} />
      </Section>

      <Section title="낙찰 · 즉시구매 · 노출" method="POST /items/{id}/close · buy-now · spotlight">
        <div className="actions">
          <button onClick={() => closeItem.run()}>조기 마감 (판매자)</button>
          <button className="btn-primary" onClick={() => buyNow.run()}>
            즉시구매
          </button>
          <button onClick={() => spotlight.run()}>상단 노출권 (포인트)</button>
        </div>
        <Result {...closeItem} />
        <Result {...buyNow} />
        <Result {...spotlight} />
      </Section>

      <Section title="입찰 — 일반 경매" method="POST /items/{id}/bids">
        <Field
          label="입찰가"
          type="number"
          value={bidAmount}
          onChange={(e) => setBidAmount(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => createBid.run()}>
            입찰
          </button>
          <button onClick={() => listBids.run()}>입찰 이력</button>
          <button onClick={() => myBids.run()}>내 입찰</button>
        </div>
        <Result {...createBid} />
        <Result {...listBids} />
        <Result {...myBids} />
        <Field label="bid_id" value={bidId} onChange={(e) => setBidId(e.target.value)} />
        <div className="actions">
          <button onClick={() => cancelBid.run()}>입찰 취소</button>
        </div>
        <Result {...cancelBid} />
      </Section>

      <Section title="입찰 — 블라인드 경매" method="POST /items/{id}/blind-bids">
        <Field
          label="입찰가 (비공개)"
          type="number"
          value={blindAmount}
          onChange={(e) => setBlindAmount(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => createBlind.run()}>
            밀봉 입찰
          </button>
          <button onClick={() => myRank.run()}>내 순위</button>
          <button onClick={() => blindResults.run()}>결과 (마감 후)</button>
        </div>
        <Result {...createBlind} />
        <Result {...myRank} />
        <Result {...blindResults} />
        <Field
          label="blind_bid_id"
          value={blindBidId}
          onChange={(e) => setBlindBidId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => cancelBlind.run()}>입찰 취소</button>
        </div>
        <Result {...cancelBlind} />
      </Section>

      <Section
        title="AI 보조 (API 콘솔)"
        method="GET /ai/price-suggestion · POST /ai/abuse-check"
      >
        <p className="hint">
          LLM 없이 과거 낙찰가 통계와 규칙 기반으로 시세·어뷰징 여부를
          제안합니다. 설명 자동 생성은 위 상품 등록 폼의 &quot;AI 설명 제안
          받기&quot; 버튼에서 바로 사용할 수 있습니다.
        </p>
        <Field
          label="category"
          value={aiCategory}
          onChange={(e) => setAiCategory(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => priceSuggestion.run()}>시세 추천</button>
        </div>
        <Result {...priceSuggestion} />
        <Field
          label="설명 문구"
          value={aiText}
          onChange={(e) => setAiText(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => abuseCheck.run()}>어뷰징 문구 탐지</button>
        </div>
        <Result {...abuseCheck} />
      </Section>

      <Section title="실시간 입찰" method="WS /items/{id}/bid">
        <p className="hint">
          연결하면 스냅샷을 받고, 다른 탭·사용자의 입찰이 실시간으로
          로그에 들어옵니다.
        </p>
        <div className="actions">
          <button onClick={wsConnect}>연결</button>
          <button onClick={wsDisconnect}>끊기</button>
        </div>
        <Field
          label="입찰가"
          type="number"
          value={wsAmount}
          onChange={(e) => setWsAmount(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={wsSendBid}>
            WS 입찰 전송
          </button>
        </div>
        <div className="resp">
          <div className="resp__label">
            <span className="dot" />
            WS 로그
          </div>
          <pre style={{ maxHeight: 220, overflowY: "auto" }}>
            {wsLog.join("\n") || "연결 대기 중…"}
          </pre>
        </div>
      </Section>
    </div>
  );
}
