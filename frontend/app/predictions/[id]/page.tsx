"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, getToken } from "../../lib/api";
import { Card, Countdown, Icon, useCall } from "../../lib/ui";

type Prediction = {
  id: number;
  title: string;
  description: string | null;
  end_time: string;
  status: string;
  yes_odds: number;
  no_odds: number;
  result: string | null;
  created_by: number;
};

type Odds = {
  prediction_id: number;
  yes_pool: number;
  no_pool: number;
  total_pool: number;
  yes_backers: number;
  no_backers: number;
  yes_odds: number | null;
  no_odds: number | null;
};

type Bet = {
  id: number;
  prediction_id: number;
  user_id: number;
  position: string;
  amount: number;
  result: string;
  payout: number;
  is_cancelled: boolean;
};

const STATUS_LABEL: Record<string, string> = {
  ongoing: "진행중",
  closed: "마감 (정산 대기)",
  settled: "정산 완료",
};

export default function PredictionDetailPage() {
  const params = useParams<{ id: string }>();
  const predictionId = Number(params.id);

  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [odds, setOdds] = useState<Odds | null>(null);
  const [myBets, setMyBets] = useState<Bet[]>([]);
  const [balance, setBalance] = useState<number | null>(null);

  const [position, setPosition] = useState<"yes" | "no">("yes");
  const [amount, setAmount] = useState("");
  const betCall = useCall(() =>
    api<Bet>(`/predictions/${predictionId}/bets`, {
      method: "POST",
      auth: true,
      body: { position, amount: Number(amount) },
    }),
  );
  const cancelCall = useCall((betId: number) =>
    api(`/prediction-bets/${betId}`, { method: "DELETE", auth: true }),
  );

  const loadOdds = () =>
    api<Odds>(`/predictions/${predictionId}/odds`)
      .then(setOdds)
      .catch(() => {});

  const loadMyBets = () => {
    if (!getToken()) return;
    api<Bet[]>("/users/me/prediction-bets", { auth: true })
      .then((list) => setMyBets(list.filter((b) => b.prediction_id === predictionId)))
      .catch(() => {});
    api<{ balance: number }>("/users/me/points/balance", { auth: true })
      .then((r) => setBalance(r.balance))
      .catch(() => {});
  };

  useEffect(() => {
    api<Prediction>(`/predictions/${predictionId}`)
      .then(setPrediction)
      .catch((e) => setLoadError(String(e)));
    loadOdds();
    loadMyBets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predictionId]);

  const submitBet = async () => {
    const res = await betCall.run();
    if (res) {
      setAmount("");
      loadOdds();
      loadMyBets();
    }
  };
  const submitCancel = async (betId: number) => {
    const res = await cancelCall.run(betId);
    if (res !== undefined) {
      loadOdds();
      loadMyBets();
    }
  };

  if (loadError) return <div className="empty">{loadError}</div>;
  if (!prediction) return <div className="empty">불러오는 중…</div>;

  const isOngoing = prediction.status === "ongoing";
  const yesShare = odds && odds.total_pool > 0 ? (odds.yes_pool / odds.total_pool) * 100 : 50;
  const noShare = 100 - yesShare;

  return (
    <div>
      <div className="detail-head">
        <div>
          <span className="cat">예측시장 · {STATUS_LABEL[prediction.status] ?? prediction.status}</span>
          <h1>{prediction.title}</h1>
        </div>
        {isOngoing ? (
          <Countdown endTime={prediction.end_time} />
        ) : (
          <span className="badge badge--red">
            {prediction.result ? `결과: ${prediction.result.toUpperCase()}` : "정산 대기"}
          </span>
        )}
      </div>

      {prediction.description && <p>{prediction.description}</p>}

      <Card
        title="배당 현황"
        right={balance !== null ? <span className="pointpill">{balance.toLocaleString()} P</span> : undefined}
      >
        <div className="oddsgauge">
          <div className="seg yes" style={{ flexBasis: `${yesShare}%` }}>
            {yesShare > 12 && `YES ${yesShare.toFixed(0)}%`}
          </div>
          <div className="seg no" style={{ flexBasis: `${noShare}%` }}>
            {noShare > 12 && `NO ${noShare.toFixed(0)}%`}
          </div>
        </div>
        <div className="oddsrow">
          <span>
            YES 배당 <b>{odds?.yes_odds ? `${odds.yes_odds.toFixed(2)}배` : "-"}</b> · 참여{" "}
            {odds?.yes_backers ?? 0}명
          </span>
          <span>
            NO 배당 <b>{odds?.no_odds ? `${odds.no_odds.toFixed(2)}배` : "-"}</b> · 참여{" "}
            {odds?.no_backers ?? 0}명
          </span>
        </div>

        {isOngoing && (
          <>
            <div className="row bidform">
              <select value={position} onChange={(e) => setPosition(e.target.value as "yes" | "no")}>
                <option value="yes">YES</option>
                <option value="no">NO</option>
              </select>
              <input
                type="number"
                placeholder="베팅 포인트"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <button className="btn btn-primary" onClick={submitBet} disabled={betCall.loading || !amount}>
                베팅
              </button>
            </div>
            {betCall.error && <p className="hint hint--error">{betCall.error}</p>}
          </>
        )}
      </Card>

      <Card title="내 베팅 내역">
        {myBets.length === 0 ? (
          <div className="empty">참여한 베팅이 없습니다.</div>
        ) : (
          <ul className="bidlist">
            {myBets.map((b) => (
              <li key={b.id}>
                <span>
                  {b.position.toUpperCase()} · {b.amount.toLocaleString()}P
                  {b.is_cancelled && " (취소됨)"}
                  {b.result !== "pending" && !b.is_cancelled && ` — ${b.result} (${b.payout.toLocaleString()}P)`}
                </span>
                {isOngoing && !b.is_cancelled && (
                  <button className="btn btn-sm" onClick={() => submitCancel(b.id)} disabled={cancelCall.loading}>
                    취소
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        {cancelCall.error && <p className="hint hint--error">{cancelCall.error}</p>}
      </Card>

      <p>
        <Link href="/predictions" className="back-link">
          <Icon name="back" size={14} /> 목록으로
        </Link>
      </p>
    </div>
  );
}
