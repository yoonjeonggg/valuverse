"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { Card, PageHeader, useCall } from "../lib/ui";

type SkillItemRow = { id: number; title: string; category: string | null; start_price: number; status: string };

const STATUS_LABEL: Record<string, string> = {
  recruiting: "모집중",
  awarded: "예약 확정",
  closed: "거래 종료",
};

export default function SkillItemsPage() {
  const [feed, setFeed] = useState<SkillItemRow[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("recruiting");

  const loadFeed = (status: string) =>
    api<SkillItemRow[]>("/skill-items", { query: { status } })
      .then(setFeed)
      .catch(() => setFeed([]));

  useEffect(() => {
    loadFeed(statusFilter);
  }, [statusFilter]);

  const [category, setCategory] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startPrice, setStartPrice] = useState("10000");
  const [durationMinutes, setDurationMinutes] = useState("60");
  const [provideType, setProvideType] = useState("");
  const [availableSchedule, setAvailableSchedule] = useState("");

  const create = useCall(() =>
    api("/skill-items", {
      method: "POST",
      auth: true,
      body: {
        title,
        description: description || undefined,
        category: category || undefined,
        start_price: Number(startPrice),
        duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
        provide_type: provideType || undefined,
        available_schedule: availableSchedule || undefined,
      },
    }),
  );
  const submitCreate = async () => {
    const res = await create.run();
    if (res) {
      setTitle("");
      setDescription("");
      loadFeed(statusFilter);
    }
  };

  const skillTag = useCall(() =>
    api<{ suggested_category: string; suggested_level: string }>("/ai/skill-tag-suggestion", {
      method: "POST",
      auth: true,
      body: { intro_text: description },
    }),
  );

  return (
    <div>
      <PageHeader eyebrow="Skill Auction" title="스킬 경매">
        <p>
          무형의 재능을 거래합니다. 예약 생성이 곧 낙찰이며, 낙찰금은
          에스크로에 보관됐다가 완료·노쇼에 따라 정산·환불됩니다.
        </p>
      </PageHeader>

      <Card
        title="스킬 상품"
        right={
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="recruiting">모집중</option>
            <option value="awarded">예약 확정</option>
            <option value="closed">거래 종료</option>
          </select>
        }
      >
        {feed === null ? (
          <div className="empty">불러오는 중…</div>
        ) : feed.length === 0 ? (
          <div className="empty">해당 상태의 스킬 상품이 없습니다.</div>
        ) : (
          <div className="item-grid">
            {feed.map((it) => (
              <Link key={it.id} href={`/skill-items/${it.id}`} className="item-card">
                <span className="cat">{it.category || "미분류"}</span>
                <span className="ttl">{it.title}</span>
                <span className="price">
                  {it.start_price.toLocaleString()}원
                  {it.status !== "recruiting" && ` · ${STATUS_LABEL[it.status] ?? it.status}`}
                </span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Card title="스킬 상품 등록">
        <div className="field">
          <span>제목</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <span>소개글</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="actions">
          <button className="btn-sm" onClick={() => skillTag.run()} disabled={!description || skillTag.loading}>
            AI 카테고리/난이도 제안
          </button>
        </div>
        {skillTag.data && (
          <div className="card" style={{ margin: 0 }}>
            <p className="hint">
              제안 카테고리 <b>{skillTag.data.suggested_category}</b> · 난이도{" "}
              <b>{skillTag.data.suggested_level}</b>
            </p>
            <div className="actions">
              <button className="btn-sm" onClick={() => setCategory(skillTag.data!.suggested_category)}>
                카테고리 적용
              </button>
            </div>
          </div>
        )}
        <div className="field">
          <span>카테고리</span>
          <input value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
        <div className="field">
          <span>가격</span>
          <input type="number" value={startPrice} onChange={(e) => setStartPrice(e.target.value)} />
        </div>
        <div className="field">
          <span>소요 시간(분)</span>
          <input
            type="number"
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
          />
        </div>
        <div className="field">
          <span>제공 형태</span>
          <input
            value={provideType}
            onChange={(e) => setProvideType(e.target.value)}
            placeholder="온라인/오프라인 등"
          />
        </div>
        <div className="field">
          <span>가능 일정</span>
          <input
            value={availableSchedule}
            onChange={(e) => setAvailableSchedule(e.target.value)}
            placeholder="예: 평일 저녁, 주말"
          />
        </div>
        <div className="actions">
          <button className="btn btn-primary" onClick={submitCreate} disabled={create.loading || !title}>
            등록
          </button>
        </div>
        {create.error && <p className="hint hint--error">{create.error}</p>}
      </Card>
    </div>
  );
}
