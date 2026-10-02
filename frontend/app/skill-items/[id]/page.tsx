import { serverGet } from "../../lib/server-api";
import type { Review, SkillItem } from "../../lib/types";
import { SkillItemView } from "./skill-item-view";

export default async function SkillItemDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [item, reviews] = await Promise.all([
    serverGet<SkillItem>(`/skill-items/${encodeURIComponent(id)}`),
    serverGet<Review[]>("/reviews", { skill_item_id: id }),
  ]);
  return <SkillItemView initialItem={item} initialReviews={reviews} />;
}
