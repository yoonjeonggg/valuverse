"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "../lib/api";
import { Card, PageHeader } from "../lib/ui";

type Review = {
  id: number;
  author_id: number;
  target_user_id: number;
  item_id: number | null;
  skill_item_id: number | null;
  rating: number;
  content: string | null;
  created_at: string;
};

export default function ReviewsPage() {
  const [meId, setMeId] = useState<number | null>(null);
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoadError("로그인하면 내가 받은 리뷰를 볼 수 있습니다.");
      return;
    }
    api<{ id: number }>("/users/me", { auth: true })
      .then((u) => {
        setMeId(u.id);
        return api<Review[]>("/reviews", { query: { target_user_id: u.id } });
      })
      .then(setReviews)
      .catch((e) => setLoadError(String(e)));
  }, []);

  const avg =
    reviews && reviews.length > 0
      ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
      : null;

  return (
    <div>
      <PageHeader eyebrow="Trust" title="내가 받은 리뷰">
        <p>
          완료된 거래(낙찰 / 스킬 완료)의 상대방이 남긴 후기입니다. 리뷰 작성은
          해당 상품·스킬 상세 화면에서 할 수 있습니다.
        </p>
      </PageHeader>

      <Card
        title="리뷰"
        right={avg !== null ? <span className="pointpill">평균 {avg.toFixed(1)} / 5</span> : undefined}
      >
        {loadError ? (
          <div className="empty">{loadError}</div>
        ) : !reviews ? (
          <div className="empty">불러오는 중…</div>
        ) : reviews.length === 0 ? (
          <div className="empty">아직 받은 리뷰가 없습니다.</div>
        ) : (
          <ul className="reviewlist">
            {reviews.map((r) => (
              <li key={r.id}>
                <span className="rating">{r.rating}/5</span>
                <span className="meta">
                  {r.author_id === meId ? "나" : `작성자 #${r.author_id}`} ·{" "}
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
                {r.content && <p>{r.content}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
