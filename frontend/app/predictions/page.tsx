"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { toIso } from "../lib/format";
import { Card, Field, PageHeader, Result, Section, useCall } from "../lib/ui";

type PredictionRow = { id: number; title: string; end_time: string; status: string };

export default function PredictionsPage() {
  const [feed, setFeed] = useState<PredictionRow[] | null>(null);
  useEffect(() => {
    api<PredictionRow[]>("/predictions", { query: { status: "ongoing" } })
      .then(setFeed)
      .catch(() => setFeed([]));
  }, []);

  const [statusFilter, setStatusFilter] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [endTime, setEndTime] = useState("");
  const [yesOdds, setYesOdds] = useState("2.0");
  const [noOdds, setNoOdds] = useState("2.0");

  const [predictionId, setPredictionId] = useState("");
  const [patchStatus, setPatchStatus] = useState("closed");
  const [patchResult, setPatchResult] = useState("yes");
  const [settleResult, setSettleResult] = useState("yes");

  const [position, setPosition] = useState("yes");
  const [amount, setAmount] = useState("");
  const [betId, setBetId] = useState("");

  const list = useCall(() =>
    api("/predictions", { query: { status: statusFilter } }),
  );
  const create = useCall(() =>
    api("/predictions", {
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
  const getOne = useCall(() => api(`/predictions/${Number(predictionId)}`));
  const patch = useCall(() =>
    api(`/predictions/${Number(predictionId)}`, {
      method: "PATCH",
      auth: true,
      body: {
        status: patchStatus || undefined,
        result: patchResult || undefined,
      },
    }),
  );
  const del = useCall(() =>
    api(`/predictions/${Number(predictionId)}`, { method: "DELETE", auth: true }),
  );
  const odds = useCall(() => api(`/predictions/${Number(predictionId)}/odds`));
  const settle = useCall(() =>
    api(`/predictions/${Number(predictionId)}/settle`, {
      method: "POST",
      auth: true,
      body: { result: settleResult },
    }),
  );

  const createBet = useCall(() =>
    api(`/predictions/${Number(predictionId)}/bets`, {
      method: "POST",
      auth: true,
      body: { position, amount: Number(amount) },
    }),
  );
  const myBets = useCall(() =>
    api("/users/me/prediction-bets", { auth: true }),
  );
  const cancelBet = useCall(() =>
    api(`/prediction-bets/${Number(betId)}`, { method: "DELETE", auth: true }),
  );

  return (
    <div>
      <PageHeader eyebrow="Prediction Market" title="예측시장">
        <p>
          Yes / No 명제에 포인트를 베팅하고, 파리뮤추얼 방식으로 정산받습니다.
          명제 등록·수정·정산은 관리자 계정이 필요합니다.
        </p>
      </PageHeader>

      <Card title="진행중인 명제">
        {feed === null ? (
          <div className="empty">불러오는 중…</div>
        ) : feed.length === 0 ? (
          <div className="empty">진행중인 명제가 없습니다.</div>
        ) : (
          <div className="item-grid">
            {feed.map((p) => (
              <Link key={p.id} href={`/predictions/${p.id}`} className="item-card">
                <span className="cat">예측시장</span>
                <span className="ttl">{p.title}</span>
                <span className="meta">
                  마감 {new Date(p.end_time).toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Section title="명제 목록 (API 콘솔)" method="GET /predictions">
        <Field
          label="status (ongoing/closed/settled)"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => list.run()}>목록 조회</button>
        </div>
        <Result {...list} />
      </Section>

      <Section title="명제 등록" method="POST /predictions · 관리자">
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
          label="yes_odds (>1.0)"
          type="number"
          value={yesOdds}
          onChange={(e) => setYesOdds(e.target.value)}
        />
        <Field
          label="no_odds (>1.0)"
          type="number"
          value={noOdds}
          onChange={(e) => setNoOdds(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => create.run()}>
            등록
          </button>
        </div>
        <Result {...create} />
      </Section>

      <Section title="대상 명제 선택" method="GET · PATCH · DELETE /predictions/{id}">
        <Field
          label="prediction_id"
          value={predictionId}
          onChange={(e) => setPredictionId(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => getOne.run()}>조회</button>
          <button onClick={() => del.run()}>삭제 (관리자)</button>
        </div>
        <Field
          label="patch status"
          value={patchStatus}
          onChange={(e) => setPatchStatus(e.target.value)}
        />
        <Field
          label="patch result (yes/no)"
          value={patchResult}
          onChange={(e) => setPatchResult(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => patch.run()}>수정 (관리자)</button>
        </div>
        <Result {...getOne} />
        <Result {...patch} />
        <Result {...del} />
      </Section>

      <Section title="배당률 · 정산" method="GET /odds · POST /settle">
        <div className="actions">
          <button onClick={() => odds.run()}>배당률 조회</button>
        </div>
        <Result {...odds} />
        <Field
          label="정산 결과 (yes/no)"
          value={settleResult}
          onChange={(e) => setSettleResult(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => settle.run()}>
            정산 (관리자, 마감 후)
          </button>
        </div>
        <Result {...settle} />
      </Section>

      <Section title="베팅" method="POST /predictions/{id}/bets">
        <Field
          label="포지션 (yes/no)"
          value={position}
          onChange={(e) => setPosition(e.target.value)}
        />
        <Field
          label="금액"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <div className="actions">
          <button className="btn-primary" onClick={() => createBet.run()}>
            베팅
          </button>
          <button onClick={() => myBets.run()}>내 베팅 내역</button>
        </div>
        <Result {...createBet} />
        <Result {...myBets} />
        <Field label="bet_id" value={betId} onChange={(e) => setBetId(e.target.value)} />
        <div className="actions">
          <button onClick={() => cancelBet.run()}>베팅 취소</button>
        </div>
        <Result {...cancelBet} />
      </Section>
    </div>
  );
}
