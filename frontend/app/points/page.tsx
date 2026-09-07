"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function PointsPage() {
  const [amount, setAmount] = useState("1000");
  const [type, setType] = useState("charge");
  const [memo, setMemo] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const balance = useCall(() =>
    api("/users/me/points/balance", { auth: true }),
  );
  const listTx = useCall(() =>
    api("/users/me/point-transactions", {
      auth: true,
      query: { type: typeFilter },
    }),
  );
  const createTx = useCall(() =>
    api("/point-transactions", {
      method: "POST",
      auth: true,
      body: {
        user_id: targetUserId ? Number(targetUserId) : undefined,
        amount: Number(amount),
        type,
        memo: memo || undefined,
      },
    }),
  );

  return (
    <div>
      <h1>포인트 (Point)</h1>

      <Section title="GET /users/me/points/balance (인증)">
        <button onClick={() => balance.run()}>잔액 조회</button>
        <Result data={balance.data} error={balance.error} loading={balance.loading} />
      </Section>

      <Section title="POST /point-transactions (인증)">
        <Field
          label="amount (양수=적립, 음수=차감)"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <Field label="type" value={type} onChange={(e) => setType(e.target.value)} />
        <Field label="memo" value={memo} onChange={(e) => setMemo(e.target.value)} />
        <Field
          label="user_id (생략 시 본인)"
          value={targetUserId}
          onChange={(e) => setTargetUserId(e.target.value)}
        />
        <button onClick={() => createTx.run()}>생성</button>
        <Result data={createTx.data} error={createTx.error} loading={createTx.loading} />
      </Section>

      <Section title="GET /users/me/point-transactions (인증)">
        <Field
          label="type 필터"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        />
        <button onClick={() => listTx.run()}>내역 조회</button>
        <Result data={listTx.data} error={listTx.error} loading={listTx.loading} />
      </Section>
    </div>
  );
}
