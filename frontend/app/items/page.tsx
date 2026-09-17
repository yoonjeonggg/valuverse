"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { toIso } from "../lib/format";
import { Card, PageHeader, useCall } from "../lib/ui";

type ItemRow = {
  id: number;
  title: string;
  category: string | null;
  current_price: number;
  auction_type: string;
  status: string;
};

export default function ItemsPage() {
  const [feed, setFeed] = useState<ItemRow[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("ongoing");

  const loadFeed = (status: string) =>
    api<ItemRow[]>("/items", { query: { status } })
      .then(setFeed)
      .catch(() => setFeed([]));

  useEffect(() => {
    loadFeed(statusFilter);
  }, [statusFilter]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [createCategory, setCreateCategory] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [startPrice, setStartPrice] = useState("1000");
  const [buyNowPrice, setBuyNowPrice] = useState("");
  const [auctionType, setAuctionType] = useState("general");
  const [blindPriceRule, setBlindPriceRule] = useState("first");
  const [endTime, setEndTime] = useState("");

  const create = useCall(() =>
    api<{ id: number }>("/items", {
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

  const submitCreate = async () => {
    const res = await create.run();
    if (res) {
      setTitle("");
      setDescription("");
      setImageUrl("");
      setBuyNowPrice("");
      setEndTime("");
      loadFeed(statusFilter);
    }
  };

  return (
    <div>
      <PageHeader eyebrow="Auction" title="일반 · 블라인드 경매">
        <p>
          공개 실시간 입찰과 밀봉 입찰을 한 화면에서 다룹니다. 등록 시 경매
          방식과 블라인드 낙찰 규칙을 정합니다.
        </p>
      </PageHeader>

      <Card
        title="상품"
        right={
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="ongoing">진행중</option>
            <option value="closed">마감</option>
          </select>
        }
      >
        {feed === null ? (
          <div className="empty">불러오는 중…</div>
        ) : feed.length === 0 ? (
          <div className="empty">해당 상태의 상품이 없습니다.</div>
        ) : (
          <div className="item-grid">
            {feed.map((it) => (
              <Link key={it.id} href={`/items/${it.id}`} className="item-card">
                <span className="cat">
                  {it.auction_type === "blind" ? "블라인드" : "일반"} · {it.category || "미분류"}
                </span>
                <span className="ttl">{it.title}</span>
                <span className="price">{it.current_price.toLocaleString()}원</span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Card title="상품 등록">
        <div className="field">
          <span>제목</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <span>설명</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="actions">
          <button
            className="btn-sm"
            onClick={() => descSuggestion.run()}
            disabled={!title || descSuggestion.loading}
          >
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
        <div className="field">
          <span>카테고리</span>
          <input value={createCategory} onChange={(e) => setCreateCategory(e.target.value)} />
        </div>
        <div className="field">
          <span>이미지 URL</span>
          <input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} />
        </div>
        <div className="field">
          <span>시작가</span>
          <input type="number" value={startPrice} onChange={(e) => setStartPrice(e.target.value)} />
        </div>
        <div className="field">
          <span>즉시구매가 (선택)</span>
          <input
            type="number"
            value={buyNowPrice}
            onChange={(e) => setBuyNowPrice(e.target.value)}
          />
        </div>
        <div className="field">
          <span>경매 방식</span>
          <select value={auctionType} onChange={(e) => setAuctionType(e.target.value)}>
            <option value="general">일반 (공개 실시간)</option>
            <option value="blind">블라인드 (밀봉)</option>
          </select>
        </div>
        {auctionType === "blind" && (
          <div className="field">
            <span>블라인드 낙찰 규칙</span>
            <select value={blindPriceRule} onChange={(e) => setBlindPriceRule(e.target.value)}>
              <option value="first">1st-price</option>
              <option value="second">Vickrey (2nd-price)</option>
            </select>
          </div>
        )}
        <div className="field">
          <span>마감 시간</span>
          <input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
        </div>
        <div className="actions">
          <button
            className="btn btn-primary"
            onClick={submitCreate}
            disabled={create.loading || !title || !endTime}
          >
            등록
          </button>
        </div>
        {create.error && <p className="hint hint--error">{create.error}</p>}
      </Card>
    </div>
  );
}
