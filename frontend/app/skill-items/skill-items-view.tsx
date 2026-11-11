"use client";

import { useState } from "react";
import { api, apiPost } from "../lib/api";
import { SkillCard, type SkillCardItem } from "../lib/cards";
import { toIso } from "../lib/format";
import type { SkillItem } from "../lib/types";
import { Card, ErrorText, Field, Loadable, PageHeader, useCall, useLoad } from "../lib/ui";

const STATUS_LABEL: Record<string, string> = {
  recruiting: "입찰중",
  awarded: "낙찰",
  closed: "종료",
};

export function SkillItemsView({ initialFeed }: { initialFeed: SkillCardItem[] | null }) {
  const [statusFilter, setStatusFilter] = useState("recruiting");
  // 서버에서 받은 첫 목록(모집중)이 있으면 마운트 직후의 같은 요청은 건너뛴다.
  const feed = useLoad<SkillCardItem[]>(
    () => api<SkillItem[]>("/skill-items", { query: { status: statusFilter } }),
    [statusFilter],
    { initial: initialFeed },
  );

  const [category, setCategory] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startPrice, setStartPrice] = useState("10000");
  const [durationMinutes, setDurationMinutes] = useState("60");
  const [provideType, setProvideType] = useState("");
  const [availableSchedule, setAvailableSchedule] = useState("");
  const [endTime, setEndTime] = useState("");

  const create = useCall(() =>
    apiPost("/skill-items", {
      title,
      description: description || undefined,
      category: category || undefined,
      start_price: Number(startPrice),
      duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
      provide_type: provideType || undefined,
      available_schedule: availableSchedule || undefined,
      end_time: toIso(endTime),
    }),
  );
  const submitCreate = async () => {
    const res = await create.run();
    if (res) {
      setTitle("");
      setDescription("");
      feed.reload();
    }
  };

  const skillTag = useCall(() =>
    apiPost<{ suggested_category: string; suggested_level: string }>("/ai/skill-tag-suggestion", { intro_text: description }),
  );

  return (
    <div>
      <PageHeader title="스킬 경매">
        <p>
          무형의 재능을 경매로 거래합니다. 마감 시 최고 입찰자가 낙찰되고, 판매자와 일정을
          잡아 예약하면 낙찰금이 에스크로에 보관됐다가 완료·노쇼에 따라 정산·환불됩니다.
        </p>
      </PageHeader>

      <Card
        title="스킬 상품"
        right={
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="recruiting">입찰중</option>
            <option value="awarded">낙찰 (예약 진행)</option>
            <option value="closed">종료</option>
          </select>
        }
      >
        <Loadable
          data={feed.data}
          error={feed.error}
          onRetry={feed.reload}
          empty="해당 상태의 스킬 상품이 없습니다."
        >
          {(list) => (
            <div className="item-grid">
              {list.map((it) => (
                <SkillCard
                  key={it.id}
                  item={it}
                  priceSuffix={
                    it.status !== "recruiting"
                      ? ` · ${STATUS_LABEL[it.status] ?? it.status}`
                      : undefined
                  }
                />
              ))}
            </div>
          )}
        </Loadable>
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
          label="시작가"
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
        <Field
          label="입찰 마감 시간"
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
