"use client";

import { api } from "../lib/api";
import { fetchMe, useHasToken } from "../lib/me";
import type { Review } from "../lib/types";
import { Card, Loadable, PageHeader, useLoad } from "../lib/ui";

export default function ReviewsPage() {
  const hasToken = useHasToken();
  const load = useLoad(
    async () => {
      const me = await fetchMe();
      const reviews = await api<Review[]>("/reviews", { query: { target_user_id: me.id } });
      return { meId: me.id, reviews };
    },
    [],
    { enabled: !!hasToken },
  );
  const reviews = hasToken ? (load.data?.reviews ?? null) : null;

  const avg =
    reviews && reviews.length > 0
      ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
      : null;

  return (
    <div>
      <PageHeader title="내가 받은 리뷰">
        <p>
          완료된 거래(낙찰 / 스킬 완료)의 상대방이 남긴 후기입니다. 리뷰 작성은
          해당 상품·스킬 상세 화면에서 할 수 있습니다.
        </p>
      </PageHeader>

      <Card
        title="리뷰"
        right={avg !== null ? <span className="pointpill">평균 {avg.toFixed(1)} / 5</span> : undefined}
      >
        {hasToken === false ? (
          <div className="empty">로그인하면 내가 받은 리뷰를 볼 수 있습니다.</div>
        ) : (
          <Loadable data={load.data} error={load.error} onRetry={load.reload}>
            {({ meId, reviews: list }) =>
              list.length === 0 ? (
                <div className="empty">아직 받은 리뷰가 없습니다.</div>
              ) : (
                <ul className="reviewlist">
                  {list.map((r) => (
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
              )
            }
          </Loadable>
        )}
      </Card>
    </div>
  );
}
