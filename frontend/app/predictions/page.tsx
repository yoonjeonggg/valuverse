"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

function toIso(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}

export default function PredictionsPage() {
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
  const odds = useCall(() =>
    api(`/predictions/${Number(predictionId)}/odds`),
  );
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
      <h1>예측 / 베팅 (Prediction / Bet)</h1>
      <p style={{ fontSize: 13 }}>
        명제 생성/수정/삭제는 관리자(is_admin) 계정 토큰이 필요합니다.
      </p>

      <Section title="GET /predictions">
        <Field
          label="status (ongoing/closed/settled)"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <button onClick={() => list.run()}>목록 조회</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="POST /predictions (관리자)">
        <Field label="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field
          label="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Field
          label="end_time"
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
        <button onClick={() => create.run()}>등록</button>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="대상 prediction_id">
        <Field
          label="prediction_id"
          value={predictionId}
          onChange={(e) => setPredictionId(e.target.value)}
        />
        <button onClick={() => getOne.run()}>GET</button>
        <button onClick={() => del.run()}>DELETE (관리자)</button>
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
        <button onClick={() => patch.run()}>PATCH (관리자)</button>
        <Result data={getOne.data} error={getOne.error} loading={getOne.loading} />
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
        <Result data={del.data} error={del.error} loading={del.loading} />
      </Section>

      <Section title="배당률 / 정산 — 위 prediction_id 사용">
        <button onClick={() => odds.run()}>GET /predictions/{"{id}"}/odds</button>
        <Result data={odds.data} error={odds.error} loading={odds.loading} />
        <Field
          label="settle result (yes/no)"
          value={settleResult}
          onChange={(e) => setSettleResult(e.target.value)}
        />
        <button onClick={() => settle.run()}>
          POST /predictions/{"{id}"}/settle (관리자, 마감 후)
        </button>
        <Result data={settle.data} error={settle.error} loading={settle.loading} />
      </Section>

      <Section title="베팅 (Bet) — 위 prediction_id 사용">
        <Field
          label="position (yes/no)"
          value={position}
          onChange={(e) => setPosition(e.target.value)}
        />
        <Field
          label="amount"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <button onClick={() => createBet.run()}>
          POST /predictions/{"{id}"}/bets (인증)
        </button>
        <button onClick={() => myBets.run()}>
          GET /users/me/prediction-bets (인증)
        </button>
        <Result data={createBet.data} error={createBet.error} loading={createBet.loading} />
        <Result data={myBets.data} error={myBets.error} loading={myBets.loading} />
        <Field label="bet_id" value={betId} onChange={(e) => setBetId(e.target.value)} />
        <button onClick={() => cancelBet.run()}>
          DELETE /prediction-bets/{"{id}"} (인증)
        </button>
        <Result data={cancelBet.data} error={cancelBet.error} loading={cancelBet.loading} />
      </Section>
    </div>
  );
}
