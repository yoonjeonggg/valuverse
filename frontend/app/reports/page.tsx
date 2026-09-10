"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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
      <PageHeader eyebrow="Moderation" title="신고">
        <p>목록 조회·처리는 관리자(is_admin) 토큰이 필요합니다.</p>
      </PageHeader>

      <Section title="신고 접수" method="POST /reports">
        <Field
          label="target_type"
          value={targetType}
          onChange={(e) => setTargetType(e.target.value)}
        />
        <Field
          label="target_id"
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
        />
        <Field label="사유" value={reason} onChange={(e) => setReason(e.target.value)} />
        <p className="hint">
          user / item / skill_item / review 중 하나. 본인·중복 신고는 거부됩니다.
        </p>
        <div className="actions">
          <button className="btn-primary" onClick={() => create.run()}>
            신고
          </button>
        </div>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="신고 목록" method="GET /reports · 관리자">
        <Field
          label="status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <Field
          label="target_type"
          value={filterTargetType}
          onChange={(e) => setFilterTargetType(e.target.value)}
        />
        <Field
          label="target_id"
          value={filterTargetId}
          onChange={(e) => setFilterTargetId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => list.run()}>목록 조회</button>
        </div>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="신고 처리" method="PATCH /reports/{id} · 관리자">
        <p className="hint">
          status=<b>resolved</b> 로 처리하면 대상이 제재됩니다 — 상품·리뷰 삭제,
          회원은 누적 시 자동 비활성화.
        </p>
        <Field
          label="report_id"
          value={reportId}
          onChange={(e) => setReportId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => getOne.run()}>단건 조회</button>
        </div>
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
        <div className="actions">
          <button className="btn-primary" onClick={() => patch.run()}>
            처리
          </button>
        </div>
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
      </Section>
    </div>
  );
}
