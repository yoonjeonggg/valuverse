"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import { Card, PageHeader } from "../lib/ui";

type PredictionRow = { id: number; title: string; end_time: string; status: string };

const STATUS_LABEL: Record<string, string> = {
  ongoing: "진행중",
  closed: "마감 (정산 대기)",
  settled: "정산 완료",
};

export default function PredictionsPage() {
  const [statusFilter, setStatusFilter] = useState("ongoing");
  const [feed, setFeed] = useState<PredictionRow[] | null>(null);

  useEffect(() => {
    api<PredictionRow[]>("/predictions", { query: { status: statusFilter } })
      .then(setFeed)
      .catch(() => setFeed([]));
  }, [statusFilter]);

  return (
    <div>
      <PageHeader eyebrow="Prediction Market" title="예측시장">
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
                <span className="cat">예측시장 · {STATUS_LABEL[p.status] ?? p.status}</span>
                <span className="ttl">{p.title}</span>
                <span className="meta">마감 {new Date(p.end_time).toLocaleString()}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
