"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "../lib/api";
import { toIso } from "../lib/format";
import { Card, Field, PageHeader, useCall } from "../lib/ui";

type Report = {
  id: number;
  reporter_id: number;
  target_type: string;
  target_id: number;
  reason: string;
  status: string;
  admin_memo: string | null;
  created_at: string;
};

type Prediction = {
  id: number;
  title: string;
  description: string | null;
  end_time: string;
  status: string;
  yes_odds: number;
  no_odds: number;
  result: string | null;
};

type SettleResult = {
  result: string;
  total_pool: number;
  winning_pool: number;
  winners: number;
  losers: number;
  total_payout: number;
  refunded: boolean;
};

const REPORT_STATUS_LABEL: Record<string, string> = {
  pending: "대기",
  in_progress: "처리중",
  resolved: "처리완료 (제재)",
  rejected: "반려",
};

const PRED_STATUS_LABEL: Record<string, string> = {
  ongoing: "진행중",
  closed: "마감 (정산 대기)",
  settled: "정산 완료",
};

export default function AdminPage() {
  const [authChecked, setAuthChecked] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const [reports, setReports] = useState<Report[] | null>(null);
  const [reportStatusFilter, setReportStatusFilter] = useState("pending");

  const [predictions, setPredictions] = useState<Prediction[] | null>(null);
  const [settleResults, setSettleResults] = useState<Record<number, SettleResult>>({});

  const loadReports = (statusFilter: string) =>
    api<Report[]>("/reports", { auth: true, query: { status: statusFilter || undefined } }).then(
      setReports,
    );
  const loadPredictions = () => api<Prediction[]>("/predictions").then(setPredictions);

  useEffect(() => {
    if (!getToken()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthChecked(true);
      setAuthError("로그인이 필요합니다.");
      return;
    }
    loadReports("pending")
      .then(() => {
        setIsAdmin(true);
        return loadPredictions();
      })
      .catch((e) => setAuthError(e instanceof Error ? e.message : String(e)))
      .finally(() => setAuthChecked(true));
  }, []);

  const updateReportCall = useCall((id: number, status: string) =>
    api<Report>(`/reports/${id}`, { method: "PATCH", auth: true, body: { status } }),
  );
  const submitReportUpdate = async (id: number, status: string) => {
    const res = await updateReportCall.run(id, status);
    if (res) loadReports(reportStatusFilter);
  };

  const changeReportFilter = (statusFilter: string) => {
    setReportStatusFilter(statusFilter);
    loadReports(statusFilter).catch(() => {});
  };

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [endTime, setEndTime] = useState("");
  const [yesOdds, setYesOdds] = useState("2.0");
  const [noOdds, setNoOdds] = useState("2.0");
  const createPredictionCall = useCall(() =>
    api<Prediction>("/predictions", {
      method: "POST",
      auth: true,
      body: {
        title,
        description: description || undefined,
        end_time: toIso(endTime),
        yes_odds: Number(yesOdds),
        no_odds: Number(noOdds),
      },
    }),
  );
  const submitCreatePrediction = async () => {
    const res = await createPredictionCall.run();
    if (res) {
      setTitle("");
      setDescription("");
      loadPredictions();
    }
  };

  const closePredictionCall = useCall((id: number) =>
    api<Prediction>(`/predictions/${id}`, {
      method: "PATCH",
      auth: true,
      body: { status: "closed" },
    }),
  );
  const submitClose = async (id: number) => {
    const res = await closePredictionCall.run(id);
    if (res) loadPredictions();
  };

  const [settleChoice, setSettleChoice] = useState<Record<number, "yes" | "no">>({});
  const settleCall = useCall((id: number, result: "yes" | "no") =>
    api<SettleResult>(`/predictions/${id}/settle`, {
      method: "POST",
      auth: true,
      body: { result },
    }),
  );
  const submitSettle = async (id: number) => {
    const result = settleChoice[id] ?? "yes";
    const res = await settleCall.run(id, result);
    if (res) {
      setSettleResults((prev) => ({ ...prev, [id]: res }));
      loadPredictions();
    }
  };

  const deletePredictionCall = useCall((id: number) =>
    api(`/predictions/${id}`, { method: "DELETE", auth: true }),
  );
  const submitDelete = async (id: number) => {
    const res = await deletePredictionCall.run(id);
    if (res !== undefined) loadPredictions();
  };

  return (
    <div>
      <PageHeader eyebrow="Admin" title="관리자 대시보드">
        <p>신고 처리와 예측시장 명제 등록·정산을 관리합니다. 관리자 계정으로만 접근할 수 있습니다.</p>
      </PageHeader>

      {!authChecked ? (
        <div className="empty">확인 중…</div>
      ) : !isAdmin ? (
        <div className="empty">{authError ?? "관리자 권한이 필요합니다."}</div>
      ) : (
        <>
          <Card
            title="신고 처리"
            right={
              <select
                value={reportStatusFilter}
                onChange={(e) => changeReportFilter(e.target.value)}
              >
                <option value="pending">대기</option>
                <option value="in_progress">처리중</option>
                <option value="resolved">처리완료</option>
                <option value="rejected">반려</option>
                <option value="">전체</option>
              </select>
            }
          >
            {!reports || reports.length === 0 ? (
              <div className="empty">해당 상태의 신고가 없습니다.</div>
            ) : (
              reports.map((r) => (
                <div className="adminrow" key={r.id}>
                  <div className="top">
                    <span className="title">
                      {r.target_type} #{r.target_id}
                    </span>
                    <span className="badge badge--red">{REPORT_STATUS_LABEL[r.status] ?? r.status}</span>
                  </div>
                  <p className="reason">{r.reason}</p>
                  <p className="meta">
                    신고자 #{r.reporter_id} · {new Date(r.created_at).toLocaleString()}
                  </p>
                  {r.status === "pending" || r.status === "in_progress" ? (
                    <div className="actions">
                      {r.status === "pending" && (
                        <button
                          className="btn-sm"
                          onClick={() => submitReportUpdate(r.id, "in_progress")}
                          disabled={updateReportCall.loading}
                        >
                          처리중으로
                        </button>
                      )}
                      <button
                        className="btn-sm btn-primary"
                        onClick={() => submitReportUpdate(r.id, "resolved")}
                        disabled={updateReportCall.loading}
                      >
                        처리완료 (제재)
                      </button>
                      <button
                        className="btn-sm"
                        onClick={() => submitReportUpdate(r.id, "rejected")}
                        disabled={updateReportCall.loading}
                      >
                        반려
                      </button>
                    </div>
                  ) : null}
                </div>
              ))
            )}
            {updateReportCall.error && <p className="hint hint--error">{updateReportCall.error}</p>}
          </Card>

          <Card title="예측시장 명제 등록">
            <Field label="제목" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Field
              label="설명"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Field
              label="마감 시간"
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
            <Field
              label="초기 yes_odds"
              type="number"
              value={yesOdds}
              onChange={(e) => setYesOdds(e.target.value)}
            />
            <Field
              label="초기 no_odds"
              type="number"
              value={noOdds}
              onChange={(e) => setNoOdds(e.target.value)}
            />
            <div className="actions">
              <button
                className="btn btn-primary"
                onClick={submitCreatePrediction}
                disabled={!title || !endTime || createPredictionCall.loading}
              >
                등록
              </button>
            </div>
            {createPredictionCall.error && (
              <p className="hint hint--error">{createPredictionCall.error}</p>
            )}
          </Card>

          <Card title="예측시장 명제 관리">
            {!predictions || predictions.length === 0 ? (
              <div className="empty">등록된 명제가 없습니다.</div>
            ) : (
              predictions.map((p) => (
                <div className="adminrow" key={p.id}>
                  <div className="top">
                    <span className="title">{p.title}</span>
                    <span className="badge badge--red">
                      {PRED_STATUS_LABEL[p.status] ?? p.status}
                      {p.result && ` · 결과 ${p.result.toUpperCase()}`}
                    </span>
                  </div>
                  <p className="meta">마감 {new Date(p.end_time).toLocaleString()}</p>
                  <div className="actions">
                    {p.status === "ongoing" && (
                      <button
                        className="btn-sm"
                        onClick={() => submitClose(p.id)}
                        disabled={closePredictionCall.loading}
                      >
                        마감 처리
                      </button>
                    )}
                    {p.status === "closed" && (
                      <>
                        <select
                          value={settleChoice[p.id] ?? "yes"}
                          onChange={(e) =>
                            setSettleChoice((prev) => ({
                              ...prev,
                              [p.id]: e.target.value as "yes" | "no",
                            }))
                          }
                        >
                          <option value="yes">YES 승리</option>
                          <option value="no">NO 승리</option>
                        </select>
                        <button
                          className="btn-sm btn-primary"
                          onClick={() => submitSettle(p.id)}
                          disabled={settleCall.loading}
                        >
                          정산
                        </button>
                      </>
                    )}
                    {p.status === "ongoing" && (
                      <button
                        className="btn-sm"
                        onClick={() => submitDelete(p.id)}
                        disabled={deletePredictionCall.loading}
                      >
                        삭제
                      </button>
                    )}
                  </div>
                  {settleResults[p.id] && (
                    <p className="hint">
                      정산 완료 — 승자 {settleResults[p.id].winners}명, 패자{" "}
                      {settleResults[p.id].losers}명, 총 지급 {settleResults[p.id].total_payout.toLocaleString()}P
                      {settleResults[p.id].refunded && " (승자 없음 - 전액 환불)"}
                    </p>
                  )}
                </div>
              ))
            )}
            {settleCall.error && <p className="hint hint--error">{settleCall.error}</p>}
            {deletePredictionCall.error && (
              <p className="hint hint--error">{deletePredictionCall.error}</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
