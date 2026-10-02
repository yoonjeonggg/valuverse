import { serverGet } from "../../lib/server-api";
import type { Prediction } from "../../lib/types";
import { type Odds, PredictionView } from "./prediction-view";

export default async function PredictionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const path = `/predictions/${encodeURIComponent(id)}`;
  const [prediction, odds] = await Promise.all([
    serverGet<Prediction>(path),
    serverGet<Odds>(`${path}/odds`),
  ]);
  return <PredictionView initialPrediction={prediction} initialOdds={odds} />;
}
