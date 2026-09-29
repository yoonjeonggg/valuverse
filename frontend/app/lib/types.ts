// 백엔드 응답 스키마(app/schemas/*)와 1:1 대응하는 공용 타입.

export type Me = {
  id: number;
  email: string;
  nickname: string;
  profile_image: string | null;
  points: number;
  rating: number;
  is_admin: boolean;
  created_at: string;
};

export type Item = {
  id: number;
  seller_id: number;
  title: string;
  description: string | null;
  category: string | null;
  image_url: string | null;
  start_price: number;
  buy_now_price: number | null;
  current_price: number;
  auction_type: string;
  blind_price_rule: string;
  end_time: string;
  status: string;
  winner_id: number | null;
  final_price: number | null;
};

export type Bid = {
  id: number;
  item_id: number;
  bidder_id: number;
  amount: number;
  is_cancelled: boolean;
  created_at: string;
};

export type SkillItem = {
  id: number;
  seller_id: number;
  title: string;
  description: string | null;
  category: string | null;
  start_price: number;
  duration_minutes: number | null;
  provide_type: string | null;
  available_schedule: string | null;
  end_time: string | null;
  status: string;
};

export type Booking = {
  id: number;
  skill_item_id: number;
  seller_id: number;
  buyer_id: number;
  amount: number;
  scheduled_at: string;
  status: string;
};

export type Review = {
  id: number;
  author_id: number;
  target_user_id: number;
  item_id: number | null;
  skill_item_id: number | null;
  rating: number;
  content: string | null;
  created_at: string;
};

export type Prediction = {
  id: number;
  title: string;
  description: string | null;
  end_time: string;
  status: string;
  yes_odds: number;
  no_odds: number;
  result: string | null;
  created_by: number;
};

export type Mission = {
  key: string;
  description: string;
  reward: number;
  achieved: boolean;
  claimed: boolean;
};

export type Coupon = {
  id: number;
  catalog_key: string;
  discount_percent: number;
  cost: number;
  is_used: boolean;
  expires_at: string;
};

export const PREDICTION_STATUS_LABEL: Record<string, string> = {
  ongoing: "진행중",
  closed: "마감 (정산 대기)",
  settled: "정산 완료",
};
