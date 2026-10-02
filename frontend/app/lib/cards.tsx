import Link from "next/link";
import type { Item, SkillItem } from "./types";

// 목록 카드가 쓰는 필드만. 서버 렌더 시 이것만 HTML 에 실어 보내 문서 크기를 줄인다
// (설명 전문 등은 상세 화면에서만 필요).
export type AuctionCardItem = Pick<
  Item,
  "id" | "title" | "category" | "current_price" | "auction_type" | "end_time"
>;
export type SkillCardItem = Pick<
  SkillItem,
  "id" | "title" | "category" | "start_price" | "duration_minutes" | "status"
>;

export const toAuctionCardItem = (it: Item): AuctionCardItem => ({
  id: it.id,
  title: it.title,
  category: it.category,
  current_price: it.current_price,
  auction_type: it.auction_type,
  end_time: it.end_time,
});

export const toSkillCardItem = (it: SkillItem): SkillCardItem => ({
  id: it.id,
  title: it.title,
  category: it.category,
  start_price: it.start_price,
  duration_minutes: it.duration_minutes,
  status: it.status,
});

/** 일반/블라인드 경매 목록 카드. `meta` 는 카드 하단 보조 정보(남은 시간 등). */
export function AuctionCard({
  item,
  meta,
}: {
  item: Omit<AuctionCardItem, "end_time">;
  meta?: React.ReactNode;
}) {
  return (
    <Link href={`/items/${item.id}`} className="item-card">
      <span className="cat">
        {item.auction_type === "blind" ? "블라인드" : "일반"} · {item.category || "미분류"}
      </span>
      <span className="ttl">{item.title}</span>
      <span className="price">{item.current_price.toLocaleString()}원</span>
      {/* meta 는 "N시간 남음" 처럼 현재 시각 기준이라 서버/브라우저 렌더가 다를 수 있다. */}
      {meta && <span className="meta" suppressHydrationWarning>{meta}</span>}
    </Link>
  );
}

/** 스킬 경매 목록 카드. */
export function SkillCard({
  item,
  priceSuffix,
  meta,
}: {
  item: Omit<SkillCardItem, "duration_minutes" | "status">;
  priceSuffix?: string;
  meta?: React.ReactNode;
}) {
  return (
    <Link href={`/skill-items/${item.id}`} className="item-card">
      <span className="cat">{item.category || "미분류"}</span>
      <span className="ttl">{item.title}</span>
      <span className="price">
        {item.start_price.toLocaleString()}원{priceSuffix}
      </span>
      {meta && <span className="meta">{meta}</span>}
    </Link>
  );
}
