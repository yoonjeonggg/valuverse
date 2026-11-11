"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, getToken, errorMessage, apiDelete, apiPost } from "../../lib/api";
import { ChatWidget } from "../../lib/chat-widget";
import { toIso } from "../../lib/format";
import { useMe } from "../../lib/me";
import type { Booking, Review, SkillBid, SkillItem } from "../../lib/types";
import { Card, Countdown, ErrorText, Field, Icon, useCall } from "../../lib/ui";

const ITEM_STATUS_LABEL: Record<string, string> = {
  recruiting: "입찰중",
  awarded: "낙찰 · 예약 진행",
  closed: "종료",
};

const OPEN_BOOKING = ["pending", "in_progress"];

const BOOKING_STATUS_LABEL: Record<string, string> = {
  pending: "구매자 수락 대기",
  in_progress: "진행중 (에스크로 보관중)",
  completed: "완료 (정산 완료)",
  no_show: "노쇼 종료",
  cancelled: "취소됨",
};

export function SkillItemView({
  initialItem,
  initialReviews,
}: {
  initialItem: SkillItem | null;
  initialReviews: Review[] | null;
}) {
  const params = useParams<{ id: string }>();
  const itemId = Number(params.id);

  const [item, setItem] = useState<SkillItem | null>(initialItem);
  const [loadError, setLoadError] = useState<string | null>(null);
  const meId = useMe()?.id ?? null;
  const [myBooking, setMyBooking] = useState<Booking | null>(null);
  const [reviews, setReviews] = useState<Review[] | null>(initialReviews);

  const [bids, setBids] = useState<SkillBid[]>([]);
  const [bidAmount, setBidAmount] = useState("");
  const bidCall = useCall(() =>
    apiPost<SkillBid>(`/skill-items/${itemId}/bids`, { amount: Number(bidAmount) }),
  );
  const closeCall = useCall(() => apiPost<SkillItem>(`/skill-items/${itemId}/close`));

  const loadItem = () =>
    api<SkillItem>(`/skill-items/${itemId}`)
      .then(setItem)
      .catch(() => {});
  const loadBids = () =>
    api<SkillBid[]>(`/skill-items/${itemId}/bids`)
      .then(setBids)
      .catch(() => {});

  // 구매자와 금액은 낙찰 결과로 정해지므로 판매자는 일정만 보낸다.
  const [scheduledAt, setScheduledAt] = useState("");
  const createBooking = useCall(() =>
    apiPost<Booking>("/skill-bookings", {
      skill_item_id: itemId,
      scheduled_at: toIso(scheduledAt),
    }),
  );

  const isBuyer = !!myBooking && meId === myBooking.buyer_id;

  // 예약 상태 전환(수락/완료/노쇼/취소)은 모두 응답으로 예약과 상품 상태를 다시 맞춘다.
  // (예전엔 버튼을 눌러도 화면이 그대로여서 새로고침해야 결과가 보였다.)
  const bookingAction = useCall(
    async (action: "accept" | "complete" | "no-show" | "cancel") => {
      const id = myBooking?.id;
      if (action === "cancel") {
        await apiDelete(`/skill-bookings/${id}`);
        return { ...myBooking!, status: "cancelled" };
      }
      return apiPost<Booking>(
        `/skill-bookings/${id}/${action}`,
        // 노쇼는 상대방만 신고할 수 있다: 구매자는 판매자를, 판매자는 구매자를.
        action === "no-show" ? { party: isBuyer ? "seller" : "buyer" } : undefined,
      );
    },
  );
  const runBookingAction = async (action: "accept" | "complete" | "no-show" | "cancel") => {
    const res = await bookingAction.run(action);
    if (res) {
      setMyBooking(res);
      loadItem();
    }
  };

  const [reviewRating, setReviewRating] = useState("5");
  const [reviewContent, setReviewContent] = useState("");
  const createReview = useCall(() =>
    apiPost<Review>("/reviews", {
      target_user_id:
        meId === item?.seller_id ? myBooking?.buyer_id : item?.seller_id,
      skill_item_id: itemId,
      rating: Number(reviewRating),
      content: reviewContent || undefined,
    }),
  );

  const loadReviews = () =>
    api<Review[]>("/reviews", { query: { skill_item_id: itemId } })
      .then(setReviews)
      .catch(() => setReviews([]));

  useEffect(() => {
    // 서버에서 이미 받아온 상품/리뷰는 다시 부르지 않는다.
    if (initialItem?.id !== itemId)
      api<SkillItem>(`/skill-items/${itemId}`)
        .then(setItem)
        .catch((e) => setLoadError(errorMessage(e)));
    if (!initialReviews || initialItem?.id !== itemId) loadReviews();
    loadBids();

    if (getToken()) {
      api<Booking[]>("/skill-bookings", { auth: true })
        .then((list) => {
          // 거절 후 다시 요청할 수 있어 예약이 여러 건일 수 있다: 진행중인 것, 없으면 최신 것.
          const forItem = list.filter((b) => b.skill_item_id === itemId);
          const mine = forItem.find((b) => OPEN_BOOKING.includes(b.status)) ?? forItem[0];
          if (mine) setMyBooking(mine);
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  const submitBid = async () => {
    const res = await bidCall.run();
    if (res) {
      setBidAmount("");
      // 현재가·자동 연장된 마감 시간을 다시 맞춘다.
      loadItem();
      loadBids();
    }
  };
  const submitClose = async () => {
    const res = await closeCall.run();
    if (res) setItem(res);
  };
  const submitBooking = async () => {
    const res = await createBooking.run();
    if (res) setMyBooking(res);
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
  const isWinner = meId !== null && meId === item.winner_id;
  const isRecruiting = item.status === "recruiting";
  const hasOpenBooking = !!myBooking && OPEN_BOOKING.includes(myBooking.status);
  const minBid = bids.length === 0 ? item.start_price : item.current_price + 1;

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
        <div>
          <span className="badge badge--red">{ITEM_STATUS_LABEL[item.status] ?? item.status}</span>
          {isRecruiting && <Countdown endTime={item.end_time} />}
        </div>
      </div>

      {item.description && <p>{item.description}</p>}

      <Card title="상세 정보">
        <div className="meta-grid">
          <div>
            <div className="k">시작가</div>
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

      <Card title={isRecruiting ? "입찰" : "경매 결과"}>
        <div className="price-now">
          <span className="label">{isRecruiting ? "현재가" : "낙찰가"}</span>
          {(item.final_price ?? item.current_price).toLocaleString()}원
        </div>
        {isRecruiting ? (
          <>
            <div className="row bidform">
              <input
                type="number"
                placeholder={`${minBid.toLocaleString()}원 이상`}
                value={bidAmount}
                onChange={(e) => setBidAmount(e.target.value)}
              />
              <button
                className="btn btn-primary"
                onClick={submitBid}
                disabled={bidCall.loading || isOwner || !bidAmount}
              >
                입찰
              </button>
              {isOwner && (
                <button onClick={submitClose} disabled={closeCall.loading}>
                  지금 마감
                </button>
              )}
            </div>
            <p className="hint">
              {isOwner
                ? "본인 상품에는 입찰할 수 없습니다. 지금 마감하면 현재 최고 입찰자가 낙찰됩니다."
                : "보유 포인트 이내에서 입찰할 수 있습니다. 낙찰되면 판매자가 일정을 정해 예약을 요청하고, 수락할 때 낙찰가가 에스크로에 보관됩니다."}
            </p>
            <ErrorText error={bidCall.error} />
            <ErrorText error={closeCall.error} />
          </>
        ) : (
          <p className="hint">
            {item.winner_id
              ? `낙찰 완료 — 낙찰자 #${item.winner_id}${isWinner ? " (나)" : ""}`
              : "입찰자가 없어 유찰되었습니다."}
          </p>
        )}
        {bids.length === 0 ? (
          <div className="empty">아직 입찰이 없습니다.</div>
        ) : (
          <ul className="bidlist">
            {bids.map((b) => (
              <li key={b.id} className={meId === b.bidder_id ? "mine" : undefined}>
                <span>
                  입찰자 #{b.bidder_id}
                  {meId === b.bidder_id && " (나)"}
                </span>
                <span className="amt">{b.amount.toLocaleString()}원</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {isWinner && item.status === "awarded" && !hasOpenBooking && (
        <Card title="낙찰 안내">
          <p className="hint">판매자가 일정을 정해 예약을 요청하면 이곳에서 수락할 수 있습니다.</p>
        </Card>
      )}

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
          <ErrorText error={bookingAction.error} />
        </Card>
      )}

      {isOwner && item.status === "awarded" && !hasOpenBooking && (
        <Card title="낙찰자에게 예약 요청">
          <p className="hint">
            낙찰자 #{item.winner_id}에게 일정을 정해 예약을 요청합니다. 낙찰자가 수락하면 낙찰가{" "}
            {item.final_price?.toLocaleString()}P가 낙찰자 포인트에서 차감되어 에스크로에
            보관됩니다.
          </p>
          <Field
            label="일정"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
          />
          <div className="actions">
            <button
              className="btn btn-primary"
              onClick={submitBooking}
              disabled={createBooking.loading || !scheduledAt}
            >
              예약 요청
            </button>
          </div>
          <ErrorText error={createBooking.error} />
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
            <ErrorText error={createReview.error} />
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
