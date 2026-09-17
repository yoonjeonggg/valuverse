"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Card, PageHeader, useCall } from "../lib/ui";

const TARGET_TYPES: [string, string][] = [
  ["item", "일반/블라인드 상품"],
  ["skill_item", "스킬 상품"],
  ["user", "회원"],
  ["review", "리뷰"],
];

export default function ReportsPage() {
  const [targetType, setTargetType] = useState("item");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");

  const create = useCall(() =>
    api("/reports", {
      method: "POST",
      auth: true,
      body: { target_type: targetType, target_id: Number(targetId), reason },
    }),
  );

  const submit = async () => {
    const res = await create.run();
    if (res) {
      setTargetId("");
      setReason("");
    }
  };

  return (
    <div>
      <PageHeader eyebrow="Moderation" title="신고하기">
        <p>부적절한 상품, 스킬, 회원, 리뷰를 신고합니다. 본인·중복 신고는 접수되지 않습니다.</p>
      </PageHeader>

      <Card title="신고 접수">
        <div className="field">
          <span>대상 종류</span>
          <select value={targetType} onChange={(e) => setTargetType(e.target.value)}>
            {TARGET_TYPES.map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <span>대상 ID</span>
          <input
            type="number"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder="신고할 상품/회원/리뷰의 번호"
          />
        </div>
        <div className="field">
          <span>사유</span>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="신고 사유를 입력하세요" />
        </div>
        <div className="actions">
          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={create.loading || !targetId || !reason}
          >
            신고 접수
          </button>
        </div>
        {create.data !== null && create.data !== undefined && !create.error && (
          <p className="hint">신고가 접수되었습니다. 담당자가 검토 후 처리합니다.</p>
        )}
        {create.error && <p className="hint hint--error">{create.error}</p>}
      </Card>
    </div>
  );
}
