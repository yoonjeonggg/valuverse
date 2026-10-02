"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { PREDICTION_STATUS_LABEL, type Prediction } from "../lib/types";
import { Card, PageHeader } from "../lib/ui";

export function PredictionsView({ initialFeed }: { initialFeed: Prediction[] | null }) {
  const [statusFilter, setStatusFilter] = useState("ongoing");
  const [feed, setFeed] = useState<Prediction[] | null>(initialFeed);
  // 서버에서 받은 첫 목록(진행중)이 있으면 마운트 직후의 같은 요청을 건너뛴다.
  const skipInitialLoad = useRef(initialFeed !== null);

  useEffect(() => {
    if (skipInitialLoad.current) {
      skipInitialLoad.current = false;
      return;
    }
    api<Prediction[]>("/predictions", { query: { status: statusFilter } })
      .then(setFeed)
      .catch(() => setFeed([]));
  }, [statusFilter]);

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
        {feed === null ? (
          <div className="empty">불러오는 중…</div>
        ) : feed.length === 0 ? (
          <div className="empty">해당 상태의 명제가 없습니다.</div>
        ) : (
          <div className="item-grid">
            {feed.map((p) => (
              <Link key={p.id} href={`/predictions/${p.id}`} className="item-card">
                <span className="cat">예측시장 · {PREDICTION_STATUS_LABEL[p.status] ?? p.status}</span>
                <span className="ttl">{p.title}</span>
                <span className="meta">마감 {formatDateTime(p.end_time)}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
