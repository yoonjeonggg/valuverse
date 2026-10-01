"use client";

import { useEffect, useState } from "react";
import { api, apiPost } from "../lib/api";
import { AuctionCard } from "../lib/cards";
import { toIso } from "../lib/format";
import type { Item } from "../lib/types";
import { Card, ErrorText, Field, PageHeader, SelectField, useCall } from "../lib/ui";

export default function ItemsPage() {
  const [feed, setFeed] = useState<Item[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("ongoing");

  const loadFeed = (status: string) =>
    api<Item[]>("/items", { query: { status } })
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
    apiPost<{ id: number }>("/items", {
      title,
      description: description || undefined,
      category: createCategory || undefined,
      image_url: imageUrl || undefined,
      start_price: Number(startPrice),
      buy_now_price: buyNowPrice ? Number(buyNowPrice) : undefined,
      auction_type: auctionType || undefined,
      blind_price_rule: blindPriceRule || undefined,
      end_time: toIso(endTime),
    }),
  );

  const descSuggestion = useCall(() =>
    apiPost<{ draft_description: string; suggestions: string[] }>("/ai/description-suggestion", {
      title,
      category: createCategory || undefined,
      existing_description: description || undefined,
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
      <PageHeader title="일반 · 블라인드 경매">
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
              <AuctionCard key={it.id} item={it} />
            ))}
          </div>
        )}
      </Card>

      <Card title="상품 등록">
        <Field label="제목" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field label="설명" value={description} onChange={(e) => setDescription(e.target.value)} />
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
        <Field
          label="카테고리"
          value={createCategory}
          onChange={(e) => setCreateCategory(e.target.value)}
        />
        <Field label="이미지 URL" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} />
        <Field
          label="시작가"
          type="number"
          value={startPrice}
          onChange={(e) => setStartPrice(e.target.value)}
        />
        <Field
          label="즉시구매가 (선택)"
          type="number"
          value={buyNowPrice}
          onChange={(e) => setBuyNowPrice(e.target.value)}
        />
        <SelectField
          label="경매 방식"
          value={auctionType}
          onChange={(e) => setAuctionType(e.target.value)}
          options={[
            ["general", "일반 (공개 실시간)"],
            ["blind", "블라인드 (밀봉)"],
          ]}
        />
        {auctionType === "blind" && (
          <SelectField
            label="블라인드 낙찰 규칙"
            value={blindPriceRule}
            onChange={(e) => setBlindPriceRule(e.target.value)}
            options={[
              ["first", "1st-price"],
              ["second", "Vickrey (2nd-price)"],
            ]}
          />
        )}
        <Field
          label="마감 시간"
          type="datetime-local"
          value={endTime}
          onChange={(e) => setEndTime(e.target.value)}
        />
        <div className="actions">
          <button
            className="btn btn-primary"
            onClick={submitCreate}
            disabled={create.loading || !title || !endTime}
          >
            등록
          </button>
        </div>
        <ErrorText error={create.error} />
      </Card>
    </div>
  );
}
