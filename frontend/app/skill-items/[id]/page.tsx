"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, getToken, errorMessage } from "../../lib/api";
import { ChatWidget } from "../../lib/chat-widget";
import { toIso } from "../../lib/format";
import { Card, Icon, useCall } from "../../lib/ui";

type SkillItem = {
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

type Booking = {
  id: number;
  skill_item_id: number;
  seller_id: number;
  buyer_id: number;
  amount: number;
  scheduled_at: string;
  status: string;
};

type Review = {
  id: number;
  author_id: number;
  target_user_id: number;
  skill_item_id: number | null;
  rating: number;
  content: string | null;
  created_at: string;
};

const ITEM_STATUS_LABEL: Record<string, string> = {
  recruiting: "모집중",
  awarded: "예약 진행중",
  closed: "거래 종료",
};

const BOOKING_STATUS_LABEL: Record<string, string> = {
  pending: "구매자 수락 대기",
  in_progress: "진행중 (에스크로 보관중)",
  completed: "완료 (정산 완료)",
  no_show: "노쇼 종료",
  cancelled: "취소됨",
};

export default function SkillItemDetailPage() {
  const params = useParams<{ id: string }>();
  const itemId = Number(params.id);

  const [item, setItem] = useState<SkillItem | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [meId, setMeId] = useState<number | null>(null);
  const [myBooking, setMyBooking] = useState<Booking | null>(null);
  const [reviews, setReviews] = useState<Review[] | null>(null);

  const [buyerId, setBuyerId] = useState("");
  const [bookingAmount, setBookingAmount] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const createBooking = useCall(() =>
    api<Booking>("/skill-bookings", {
      method: "POST",
      auth: true,
      body: {
        skill_item_id: itemId,
        buyer_id: Number(buyerId),
        amount: Number(bookingAmount),
        scheduled_at: toIso(scheduledAt),
      },
    }),
  );

  const isBuyer = !!myBooking && meId === myBooking.buyer_id;

  // 예약 상태 전환(수락/완료/노쇼/취소)은 모두 응답으로 예약과 상품 상태를 다시 맞춘다.
  // (예전엔 버튼을 눌러도 화면이 그대로여서 새로고침해야 결과가 보였다.)
  const bookingAction = useCall(
    async (action: "accept" | "complete" | "no-show" | "cancel") => {
      const id = myBooking?.id;
      if (action === "cancel") {
        await api(`/skill-bookings/${id}`, { method: "DELETE", auth: true });
        return { ...myBooking!, status: "cancelled" };
      }
      return api<Booking>(`/skill-bookings/${id}/${action}`, {
        method: "POST",
        auth: true,
        // 노쇼는 상대방만 신고할 수 있다: 구매자는 판매자를, 판매자는 구매자를.
        body: action === "no-show" ? { party: isBuyer ? "seller" : "buyer" } : undefined,
      });
    },
  );
  const runBookingAction = async (action: "accept" | "complete" | "no-show" | "cancel") => {
    const res = await bookingAction.run(action);
    if (res) {
      setMyBooking(res);
      api<SkillItem>(`/skill-items/${itemId}`).then(setItem).catch(() => {});
    }
  };

  const [reviewRating, setReviewRating] = useState("5");
  const [reviewContent, setReviewContent] = useState("");
  const createReview = useCall(() =>
    api<Review>("/reviews", {
      method: "POST",
      auth: true,
      body: {
        target_user_id:
          meId === item?.seller_id ? myBooking?.buyer_id : item?.seller_id,
        skill_item_id: itemId,
        rating: Number(reviewRating),
        content: reviewContent || undefined,
      },
    }),
  );

  const loadReviews = () =>
    api<Review[]>("/reviews", { query: { skill_item_id: itemId } })
      .then(setReviews)
      .catch(() => setReviews([]));

  useEffect(() => {
    api<SkillItem>(`/skill-items/${itemId}`)
      .then(setItem)
      .catch((e) => setLoadError(errorMessage(e)));
    loadReviews();

    if (getToken()) {
      api<{ id: number }>("/users/me", { auth: true })
        .then((u) => setMeId(u.id))
        .catch(() => {});
      api<Booking[]>("/skill-bookings", { auth: true })
        .then((list) => {
          const mine = list.find((b) => b.skill_item_id === itemId);
          if (mine) setMyBooking(mine);
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  const submitBooking = async () => {
    const res = await createBooking.run();
    if (res) {
      setMyBooking(res);
      setItem((it) => (it ? { ...it, status: "awarded" } : it));
    }
  };
  const submitReview = async () => {
    const res = await createReview.run();
    if (res) {
      setReviewContent("");
      loadReviews();
    }
  };

  if (loadError) return <div className="empty">{loadError}</div>;
  if (!item) return <div className="empty">불러오는 중…</div>;

  const isOwner = meId === item.seller_id;

  return (
    <div>
      <div className="detail-head">
        <div>
          <span className="cat">스킬 경매 · {item.category || "미분류"}</span>
          <h1>{item.title}</h1>
          <p className="seller">
            판매자 #{item.seller_id}
            {isOwner && " (나)"}
          </p>
        </div>
        <span className="badge badge--red">{ITEM_STATUS_LABEL[item.status] ?? item.status}</span>
      </div>

      {item.description && <p>{item.description}</p>}

      <Card title="상세 정보">
        <div className="meta-grid">
          <div>
            <div className="k">가격</div>
            <div className="v">{item.start_price.toLocaleString()}원</div>
          </div>
          <div>
            <div className="k">소요 시간</div>
            <div className="v">
              {item.duration_minutes ? `${item.duration_minutes}분` : "협의"}
            </div>
          </div>
          <div>
            <div className="k">제공 형태</div>
            <div className="v">{item.provide_type || "협의"}</div>
          </div>
          <div>
            <div className="k">가능 일정</div>
            <div className="v">{item.available_schedule || "협의"}</div>
          </div>
        </div>
      </Card>

      {myBooking && (
        <Card
          title="예약 현황"
          right={
            <span className="badge badge--warn">
              {BOOKING_STATUS_LABEL[myBooking.status] ?? myBooking.status}
            </span>
          }
        >
          <p className="hint">
            일정: {new Date(myBooking.scheduled_at).toLocaleString()} · 금액{" "}
            {myBooking.amount.toLocaleString()}P
          </p>
          {myBooking.status === "pending" && (
            <>
              <p className="hint">
                {isBuyer
                  ? `수락하면 ${myBooking.amount.toLocaleString()}P가 차감되어 거래가 끝날 때까지 에스크로에 보관됩니다.`
                  : "구매자가 수락하면 예약이 확정됩니다."}
              </p>
              <div className="actions">
                {isBuyer && (
                  <button
                    className="btn btn-primary"
                    onClick={() => runBookingAction("accept")}
                    disabled={bookingAction.loading}
                  >
                    <Icon name="check" size={16} /> 수락하고 결제
                  </button>
                )}
                <button onClick={() => runBookingAction("cancel")} disabled={bookingAction.loading}>
                  {isBuyer ? "거절" : "요청 취소"}
                </button>
              </div>
            </>
          )}
          {myBooking.status === "in_progress" && (
            <div className="actions">
              {isBuyer && (
                <button
                  className="btn btn-primary"
                  onClick={() => runBookingAction("complete")}
                  disabled={bookingAction.loading}
                >
                  완료 확인 (정산)
                </button>
              )}
              <button onClick={() => runBookingAction("no-show")} disabled={bookingAction.loading}>
                {isBuyer ? "판매자 노쇼 신고" : "구매자 노쇼 신고"}
              </button>
              <button onClick={() => runBookingAction("cancel")} disabled={bookingAction.loading}>
                예약 취소
              </button>
            </div>
          )}
          {bookingAction.error && <p className="hint hint--error">{bookingAction.error}</p>}
        </Card>
      )}

      {isOwner && item.status === "recruiting" && (
        <Card title="예약 요청 (낙찰자 지정)">
          <p className="hint">
            협의가 끝난 구매자의 회원 ID로 예약을 요청합니다. 구매자가 수락하면 낙찰금이
            구매자 포인트에서 차감되어 에스크로에 보관됩니다.
          </p>
          <div className="field">
            <span>buyer_id</span>
            <input value={buyerId} onChange={(e) => setBuyerId(e.target.value)} />
          </div>
          <div className="field">
            <span>금액</span>
            <input
              type="number"
              value={bookingAmount}
              onChange={(e) => setBookingAmount(e.target.value)}
            />
          </div>
          <div className="field">
            <span>일정</span>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
            />
          </div>
          <div className="actions">
            <button className="btn btn-primary" onClick={submitBooking} disabled={createBooking.loading}>
              예약 요청
            </button>
          </div>
          {createBooking.error && <p className="hint hint--error">{createBooking.error}</p>}
        </Card>
      )}

      <Card title="후기">
        {!reviews ? (
          <div className="empty">불러오는 중…</div>
        ) : reviews.length === 0 ? (
          <div className="empty">아직 후기가 없습니다.</div>
        ) : (
          <ul className="reviewlist">
            {reviews.map((r) => (
              <li key={r.id}>
                <span className="rating">{r.rating}/5</span>
                <span className="meta">작성자 #{r.author_id}</span>
                {r.content && <p>{r.content}</p>}
              </li>
            ))}
          </ul>
        )}

        {myBooking && myBooking.status === "completed" && (
          <>
            <hr />
            <p className="hint">완료된 거래에 대해 후기를 남길 수 있습니다.</p>
            <div className="row">
              <select value={reviewRating} onChange={(e) => setReviewRating(e.target.value)}>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>
                    {n}점
                  </option>
                ))}
              </select>
              <input
                placeholder="후기 내용"
                value={reviewContent}
                onChange={(e) => setReviewContent(e.target.value)}
                style={{ flex: 1, minWidth: 200 }}
              />
              <button className="btn btn-primary" onClick={submitReview} disabled={createReview.loading}>
                후기 등록
              </button>
            </div>
            {createReview.error && <p className="hint hint--error">{createReview.error}</p>}
          </>
        )}
      </Card>

      <p>
        <Link href="/skill-items" className="back-link">
          <Icon name="back" size={14} /> 목록으로
        </Link>
      </p>

      <ChatWidget itemId={item.id} itemType="skill_item" />
    </div>
  );
}
