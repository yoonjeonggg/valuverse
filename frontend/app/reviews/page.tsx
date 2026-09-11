"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Trust" title="리뷰">
        <p>
          <b>완료된 거래(낙찰 / 스킬 완료)의 당사자</b>만, 거래당 1회 작성할 수
          있습니다. 생성 시 item_id 또는 skill_item_id 중 하나만 지정하세요.
        </p>
      </PageHeader>

      <Section title="리뷰 작성" method="POST /reviews">
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
          label="평점 (1~5)"
          type="number"
          value={rating}
          onChange={(e) => setRating(e.target.value)}
        />
        <Field label="내용" value={content} onChange={(e) => setContent(e.target.value)} />
        <div className="actions">
          <button className="btn-primary" onClick={() => create.run()}>
            작성
          </button>
        </div>
        <Result {...create} />
      </Section>

      <Section title="리뷰 조회" method="GET /reviews">
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
        <div className="actions">
          <button onClick={() => list.run()}>목록 조회</button>
        </div>
        <Result {...list} />
      </Section>

      <Section title="리뷰 수정 / 삭제" method="PATCH · DELETE /reviews/{id}">
        <Field
          label="review_id"
          value={reviewId}
          onChange={(e) => setReviewId(e.target.value)}
        />
        <Field
          label="평점"
          type="number"
          value={patchRating}
          onChange={(e) => setPatchRating(e.target.value)}
        />
        <Field
          label="내용"
          value={patchContent}
          onChange={(e) => setPatchContent(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => patch.run()}>수정</button>
          <button onClick={() => del.run()}>삭제</button>
        </div>
        <Result {...patch} />
        <Result {...del} />
      </Section>
    </div>
  );
}
