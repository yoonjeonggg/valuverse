import { toSkillCardItem } from "../lib/cards";
import { serverGet } from "../lib/server-api";
import type { SkillItem } from "../lib/types";
import { SkillItemsView } from "./skill-items-view";

export default async function SkillItemsPage() {
  const feed = await serverGet<SkillItem[]>("/skill-items", { status: "recruiting" });
  return <SkillItemsView initialFeed={feed?.map(toSkillCardItem) ?? null} />;
}
