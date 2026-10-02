import { serverGet } from "../lib/server-api";
import type { Prediction } from "../lib/types";
import { PredictionsView } from "./predictions-view";

export default async function PredictionsPage() {
  return (
    <PredictionsView
      initialFeed={await serverGet<Prediction[]>("/predictions", { status: "ongoing" })}
    />
  );
}
