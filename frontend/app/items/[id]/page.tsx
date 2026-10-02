import { serverGet } from "../../lib/server-api";
import type { Item } from "../../lib/types";
import { ItemView } from "./item-view";

export default async function ItemDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ItemView initialItem={await serverGet<Item>(`/items/${encodeURIComponent(id)}`)} />;
}
