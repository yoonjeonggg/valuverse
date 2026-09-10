"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function ReviewsPage() {
  const [targetUserId, setTargetUserId] = useState("");
  const [itemId, setItemId] = useState("");
  const [skillItemId, setSkillItemId] = useState("");
  const [rating, setRating] = useState("5");
  const [content, setContent] = useState("");

  const [filterTargetUserId, setFilterTargetUserId] = useState("");
  const [filterItemId, setFilterItemId] = useState("");
  const [filterSkillItemId, setFilterSkillItemId] = useState("");

  const [reviewId, setReviewId] = useState("");
  const [patchRating, setPatchRating] = useState("4");
  const [patchContent, setPatchContent] = useState("");

  const create = useCall(() =>
    api("/reviews", {
      method: "POST",
      auth: true,
      body: {
        target_user_id: Number(targetUserId),
        item_id: itemId ? Number(itemId) : undefined,
        skill_item_id: skillItemId ? Number(skillItemId) : undefined,
        rating: Number(rating),
        content: content || undefined,
      },
    }),
  );
  const list = useCall(() =>
    api("/reviews", {
      query: {
        target_user_id: filterTargetUserId,
        item_id: filterItemId,
        skill_item_id: filterSkillItemId,
      },
    }),
  );
  const patch = useCall(() =>
    api(`/reviews/${Number(reviewId)}`, {
      method: "PATCH",
      auth: true,
      body: {
        rating: patchRating ? Number(patchRating) : undefined,
        content: patchContent || undefined,
      },
    }),
  );
  const del = useCall(() =>
    api(`/reviews/${Number(reviewId)}`, { method: "DELETE", auth: true }),
  );

  return (
    <div>
      <h1>리뷰 (Review)</h1>
      <p style={{ fontSize: 13 }}>
        생성 시 item_id 또는 skill_item_id 중 정확히 하나만 지정하세요. 리뷰는
        <b> 완료된 거래(낙찰/스킬 완료)의 당사자</b>만, 거래당 1회 작성할 수 있습니다.
      </p>

      <Section title="POST /reviews (인증)">
        <Field
          label="target_user_id"
          value={targetUserId}
          onChange={(e) => setTargetUserId(e.target.value)}
        />
        <Field label="item_id" value={itemId} onChange={(e) => setItemId(e.target.value)} />
        <Field
          label="skill_item_id"
          value={skillItemId}
          onChange={(e) => setSkillItemId(e.target.value)}
        />
        <Field
          label="rating (1~5)"
          type="number"
          value={rating}
          onChange={(e) => setRating(e.target.value)}
        />
        <Field label="content" value={content} onChange={(e) => setContent(e.target.value)} />
        <button onClick={() => create.run()}>작성</button>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="GET /reviews">
        <Field
          label="target_user_id"
          value={filterTargetUserId}
          onChange={(e) => setFilterTargetUserId(e.target.value)}
        />
        <Field
          label="item_id"
          value={filterItemId}
          onChange={(e) => setFilterItemId(e.target.value)}
        />
        <Field
          label="skill_item_id"
          value={filterSkillItemId}
          onChange={(e) => setFilterSkillItemId(e.target.value)}
        />
        <button onClick={() => list.run()}>목록 조회</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="대상 review_id">
        <Field
          label="review_id"
          value={reviewId}
          onChange={(e) => setReviewId(e.target.value)}
        />
        <Field
          label="patch rating"
          type="number"
          value={patchRating}
          onChange={(e) => setPatchRating(e.target.value)}
        />
        <Field
          label="patch content"
          value={patchContent}
          onChange={(e) => setPatchContent(e.target.value)}
        />
        <button onClick={() => patch.run()}>PATCH (인증)</button>
        <button onClick={() => del.run()}>DELETE (인증)</button>
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
        <Result data={del.data} error={del.error} loading={del.loading} />
      </Section>
    </div>
  );
}
