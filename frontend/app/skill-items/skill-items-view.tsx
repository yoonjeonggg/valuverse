"use client";

import { useEffect, useRef, useState } from "react";
import { api, apiPost } from "../lib/api";
import { SkillCard, type SkillCardItem } from "../lib/cards";
import type { SkillItem } from "../lib/types";
import { Card, ErrorText, Field, PageHeader, useCall } from "../lib/ui";

const STATUS_LABEL: Record<string, string> = {
  recruiting: "모집중",
  awarded: "예약 확정",
  closed: "거래 종료",
};

export function SkillItemsView({ initialFeed }: { initialFeed: SkillCardItem[] | null }) {
  const [feed, setFeed] = useState<SkillCardItem[] | null>(initialFeed);
  const [statusFilter, setStatusFilter] = useState("recruiting");
  // 서버에서 받은 첫 목록(모집중)이 있으면 마운트 직후의 같은 요청을 건너뛴다.
  const skipInitialLoad = useRef(initialFeed !== null);

  const loadFeed = (status: string) =>
    api<SkillItem[]>("/skill-items", { query: { status } })
      .then(setFeed)
      .catch(() => setFeed([]));

  useEffect(() => {
    if (skipInitialLoad.current) {
      skipInitialLoad.current = false;
      return;
    }
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
    apiPost("/skill-items", {
      title,
      description: description || undefined,
      category: category || undefined,
      start_price: Number(startPrice),
      duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
      provide_type: provideType || undefined,
      available_schedule: availableSchedule || undefined,
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
    apiPost<{ suggested_category: string; suggested_level: string }>("/ai/skill-tag-suggestion", { intro_text: description }),
  );

  return (
    <div>
      <PageHeader title="스킬 경매">
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
              <SkillCard
                key={it.id}
                item={it}
                priceSuffix={
                  it.status !== "recruiting" ? ` · ${STATUS_LABEL[it.status] ?? it.status}` : undefined
                }
              />
            ))}
          </div>
        )}
      </Card>

      <Card title="스킬 상품 등록">
        <Field label="제목" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field label="소개글" value={description} onChange={(e) => setDescription(e.target.value)} />
        <div className="actions actions--field">
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
        <Field label="카테고리" value={category} onChange={(e) => setCategory(e.target.value)} />
        <Field
          label="가격"
          type="number"
          value={startPrice}
          onChange={(e) => setStartPrice(e.target.value)}
        />
        <Field
          label="소요 시간(분)"
          type="number"
          value={durationMinutes}
          onChange={(e) => setDurationMinutes(e.target.value)}
        />
        <Field
          label="제공 형태"
          value={provideType}
          onChange={(e) => setProvideType(e.target.value)}
          placeholder="온라인/오프라인 등"
        />
        <Field
          label="가능 일정"
          value={availableSchedule}
          onChange={(e) => setAvailableSchedule(e.target.value)}
          placeholder="예: 평일 저녁, 주말"
        />
        <div className="actions">
          <button className="btn btn-primary" onClick={submitCreate} disabled={create.loading || !title}>
            등록
          </button>
        </div>
        <ErrorText error={create.error} />
      </Card>
    </div>
  );
}
