import { toAuctionCardItem } from "../lib/cards";
import { serverGet } from "../lib/server-api";
import type { Item } from "../lib/types";
import { ItemsView } from "./items-view";

export default async function ItemsPage() {
  const feed = await serverGet<Item[]>("/items", { status: "ongoing" });
  return <ItemsView initialFeed={feed?.map(toAuctionCardItem) ?? null} />;
}
