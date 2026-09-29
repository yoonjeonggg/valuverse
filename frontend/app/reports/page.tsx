"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Card, ErrorText, Field, PageHeader, SelectField, useCall } from "../lib/ui";

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
        <SelectField
          label="대상 종류"
          value={targetType}
          onChange={(e) => setTargetType(e.target.value)}
          options={TARGET_TYPES}
        />
        <Field
          label="대상 ID"
          type="number"
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          placeholder="신고할 상품/회원/리뷰의 번호"
        />
        <Field
          label="사유"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="신고 사유를 입력하세요"
        />
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
        <ErrorText error={create.error} />
      </Card>
    </div>
  );
}
