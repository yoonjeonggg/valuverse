import Link from "next/link";
import type { Item, SkillItem } from "./types";

/** 일반/블라인드 경매 목록 카드. `meta` 는 카드 하단 보조 정보(남은 시간 등). */
export function AuctionCard({
  item,
  meta,
}: {
  item: Pick<Item, "id" | "title" | "category" | "current_price" | "auction_type">;
  meta?: React.ReactNode;
}) {
  return (
    <Link href={`/items/${item.id}`} className="item-card">
      <span className="cat">
        {item.auction_type === "blind" ? "블라인드" : "일반"} · {item.category || "미분류"}
      </span>
      <span className="ttl">{item.title}</span>
      <span className="price">{item.current_price.toLocaleString()}원</span>
      {meta && <span className="meta">{meta}</span>}
    </Link>
  );
}

/** 스킬 경매 목록 카드. */
export function SkillCard({
  item,
  priceSuffix,
  meta,
}: {
  item: Pick<SkillItem, "id" | "title" | "category" | "start_price">;
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
