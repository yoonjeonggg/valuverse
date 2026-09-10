"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function ReportsPage() {
  const [targetType, setTargetType] = useState("item");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");

  const [statusFilter, setStatusFilter] = useState("");
  const [filterTargetType, setFilterTargetType] = useState("");
  const [filterTargetId, setFilterTargetId] = useState("");

  const [reportId, setReportId] = useState("");
  const [patchStatus, setPatchStatus] = useState("in_progress");
  const [adminMemo, setAdminMemo] = useState("");

  const create = useCall(() =>
    api("/reports", {
      method: "POST",
      auth: true,
      body: {
        target_type: targetType,
        target_id: Number(targetId),
        reason,
      },
    }),
  );
  const list = useCall(() =>
    api("/reports", {
      auth: true,
      query: {
        status: statusFilter,
        target_type: filterTargetType,
        target_id: filterTargetId,
      },
    }),
  );
  const getOne = useCall(() =>
    api(`/reports/${Number(reportId)}`, { auth: true }),
  );
  const patch = useCall(() =>
    api(`/reports/${Number(reportId)}`, {
      method: "PATCH",
      auth: true,
      body: { status: patchStatus, admin_memo: adminMemo || undefined },
    }),
  );

  return (
    <div>
      <h1>신고 (Report)</h1>
      <p style={{ fontSize: 13 }}>목록 조회/처리는 관리자(is_admin) 토큰이 필요합니다.</p>

      <Section title="POST /reports (인증)">
        <Field
          label="target_type (user/item/skill_item/review)"
          value={targetType}
          onChange={(e) => setTargetType(e.target.value)}
        />
        <Field
          label="target_id"
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
        />
        <Field label="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        <button onClick={() => create.run()}>신고</button>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="GET /reports (관리자)">
        <Field
          label="status (pending/in_progress/resolved/rejected)"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <Field
          label="target_type 필터"
          value={filterTargetType}
          onChange={(e) => setFilterTargetType(e.target.value)}
        />
        <Field
          label="target_id 필터"
          value={filterTargetId}
          onChange={(e) => setFilterTargetId(e.target.value)}
        />
        <button onClick={() => list.run()}>목록 조회</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="PATCH /reports/{id} (관리자)">
        <p style={{ fontSize: 13 }}>
          status=resolved 로 처리하면 대상이 제재됩니다(상품/리뷰 삭제, 회원은 누적 시 비활성화).
        </p>
        <Field
          label="report_id"
          value={reportId}
          onChange={(e) => setReportId(e.target.value)}
        />
        <button onClick={() => getOne.run()}>GET /reports/{"{id}"}</button>
        <Result data={getOne.data} error={getOne.error} loading={getOne.loading} />
        <Field
          label="status"
          value={patchStatus}
          onChange={(e) => setPatchStatus(e.target.value)}
        />
        <Field
          label="admin_memo"
          value={adminMemo}
          onChange={(e) => setAdminMemo(e.target.value)}
        />
        <button onClick={() => patch.run()}>처리</button>
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
      </Section>
    </div>
  );
}
