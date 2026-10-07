"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { PREDICTION_STATUS_LABEL, type Prediction } from "../lib/types";
import { Card, Loadable, PageHeader, useLoad } from "../lib/ui";

export function PredictionsView({ initialFeed }: { initialFeed: Prediction[] | null }) {
  const [statusFilter, setStatusFilter] = useState("ongoing");
  // 서버에서 받은 첫 목록(진행중)이 있으면 마운트 직후의 같은 요청은 건너뛴다.
  const feed = useLoad(
    () => api<Prediction[]>("/predictions", { query: { status: statusFilter } }),
    [statusFilter],
    { initial: initialFeed },
  );

  return (
    <div>
      <PageHeader title="예측시장">
        <p>Yes / No 명제에 포인트를 베팅하고, 파리뮤추얼 방식으로 정산받습니다.</p>
      </PageHeader>

      <Card
        title="명제"
        right={
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="ongoing">진행중</option>
            <option value="closed">마감 (정산 대기)</option>
            <option value="settled">정산 완료</option>
          </select>
        }
      >
        <Loadable
          data={feed.data}
          error={feed.error}
          onRetry={feed.reload}
          empty="해당 상태의 명제가 없습니다."
        >
          {(list) => (
            <div className="item-grid">
              {list.map((p) => (
                <Link key={p.id} href={`/predictions/${p.id}`} className="item-card">
                  <span className="cat">
                    예측시장 · {PREDICTION_STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  <span className="ttl">{p.title}</span>
                  <span className="meta">마감 {formatDateTime(p.end_time)}</span>
                </Link>
              ))}
            </div>
          )}
        </Loadable>
      </Card>
    </div>
  );
}
