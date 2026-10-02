import { HOME_ITEMS_QUERY, HOME_SKILL_ITEMS_QUERY, HomeView } from "./home-view";
import { toAuctionCardItem, toSkillCardItem } from "./lib/cards";
import { serverGet } from "./lib/server-api";
import type { Item, SkillItem } from "./lib/types";

export default async function Home() {
  const [items, skillItems] = await Promise.all([
    serverGet<Item[]>("/items", HOME_ITEMS_QUERY),
    serverGet<SkillItem[]>("/skill-items", HOME_SKILL_ITEMS_QUERY),
  ]);
  return (
    <HomeView
      initialItems={items?.map(toAuctionCardItem) ?? null}
      initialSkillItems={skillItems?.map(toSkillCardItem) ?? null}
    />
  );
}
