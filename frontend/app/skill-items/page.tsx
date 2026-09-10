"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { toIso } from "../lib/format";
import { Field, Result, Section, useCall } from "../lib/ui";

export default function SkillItemsPage() {
  const [category, setCategory] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startPrice, setStartPrice] = useState("10000");
  const [durationMinutes, setDurationMinutes] = useState("60");
  const [provideType, setProvideType] = useState("");
  const [availableSchedule, setAvailableSchedule] = useState("");

  const [skillItemId, setSkillItemId] = useState("");
  const [patchTitle, setPatchTitle] = useState("");

  const [buyerId, setBuyerId] = useState("");
  const [bookingAmount, setBookingAmount] = useState("10000");
  const [scheduledAt, setScheduledAt] = useState("");
  const [bookingId, setBookingId] = useState("");
  const [bookingStatus, setBookingStatus] = useState("completed");
  const [noShowParty, setNoShowParty] = useState("seller");

  const [escrowPayeeId, setEscrowPayeeId] = useState("");
  const [escrowAmount, setEscrowAmount] = useState("");
  const [escrowBookingId, setEscrowBookingId] = useState("");
  const [escrowId, setEscrowId] = useState("");
  const [escrowStatus, setEscrowStatus] = useState("settled");

  const list = useCall(() =>
    api("/skill-items", { query: { category, status: statusFilter } }),
  );
  const create = useCall(() =>
    api("/skill-items", {
      method: "POST",
      auth: true,
      body: {
        title,
        description: description || undefined,
        category: category || undefined,
        start_price: Number(startPrice),
        duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
        provide_type: provideType || undefined,
        available_schedule: availableSchedule || undefined,
      },
    }),
  );
  const getOne = useCall(() => api(`/skill-items/${Number(skillItemId)}`));
  const patch = useCall(() =>
    api(`/skill-items/${Number(skillItemId)}`, {
      method: "PATCH",
      auth: true,
      body: { title: patchTitle || undefined },
    }),
  );
  const del = useCall(() =>
    api(`/skill-items/${Number(skillItemId)}`, { method: "DELETE", auth: true }),
  );

  const createBooking = useCall(() =>
    api("/skill-bookings", {
      method: "POST",
      auth: true,
      body: {
        skill_item_id: Number(skillItemId),
        buyer_id: Number(buyerId),
        amount: Number(bookingAmount),
        scheduled_at: toIso(scheduledAt),
      },
    }),
  );
  const myBookings = useCall(() => api("/skill-bookings", { auth: true }));
  const completeBooking = useCall(() =>
    api(`/skill-bookings/${Number(bookingId)}/complete`, {
      method: "POST",
      auth: true,
    }),
  );
  const noShowBooking = useCall(() =>
    api(`/skill-bookings/${Number(bookingId)}/no-show`, {
      method: "POST",
      auth: true,
      body: { party: noShowParty },
    }),
  );
  const getBooking = useCall(() =>
    api(`/skill-bookings/${Number(bookingId)}`, { auth: true }),
  );
  const patchBooking = useCall(() =>
    api(`/skill-bookings/${Number(bookingId)}`, {
      method: "PATCH",
      auth: true,
      body: { status: bookingStatus || undefined },
    }),
  );
  const cancelBooking = useCall(() =>
    api(`/skill-bookings/${Number(bookingId)}`, { method: "DELETE", auth: true }),
  );

  const createEscrow = useCall(() =>
    api("/escrows", {
      method: "POST",
      auth: true,
      body: {
        booking_id: escrowBookingId ? Number(escrowBookingId) : undefined,
        payee_id: Number(escrowPayeeId),
        amount: Number(escrowAmount),
      },
    }),
  );
  const getEscrow = useCall(() =>
    api(`/escrows/${Number(escrowId)}`, { auth: true }),
  );
  const patchEscrow = useCall(() =>
    api(`/escrows/${Number(escrowId)}`, {
      method: "PATCH",
      auth: true,
      body: { status: escrowStatus },
    }),
  );

  return (
    <div>
      <h1>스킬상품 (Skill Item / Booking / Escrow)</h1>

      <Section title="GET /skill-items">
        <Field label="category" value={category} onChange={(e) => setCategory(e.target.value)} />
        <Field
          label="status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <button onClick={() => list.run()}>목록 조회</button>
        <Result data={list.data} error={list.error} loading={list.loading} />
      </Section>

      <Section title="POST /skill-items (인증 필요)">
        <Field label="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Field
          label="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Field
          label="start_price"
          type="number"
          value={startPrice}
          onChange={(e) => setStartPrice(e.target.value)}
        />
        <Field
          label="duration_minutes"
          type="number"
          value={durationMinutes}
          onChange={(e) => setDurationMinutes(e.target.value)}
        />
        <Field
          label="provide_type"
          value={provideType}
          onChange={(e) => setProvideType(e.target.value)}
        />
        <Field
          label="available_schedule"
          value={availableSchedule}
          onChange={(e) => setAvailableSchedule(e.target.value)}
        />
        <button onClick={() => create.run()}>등록</button>
        <Result data={create.data} error={create.error} loading={create.loading} />
      </Section>

      <Section title="대상 skill_item_id">
        <Field
          label="skill_item_id"
          value={skillItemId}
          onChange={(e) => setSkillItemId(e.target.value)}
        />
        <button onClick={() => getOne.run()}>GET</button>
        <button onClick={() => del.run()}>DELETE (인증)</button>
        <Field
          label="patch title"
          value={patchTitle}
          onChange={(e) => setPatchTitle(e.target.value)}
        />
        <button onClick={() => patch.run()}>PATCH title (인증)</button>
        <Result data={getOne.data} error={getOne.error} loading={getOne.loading} />
        <Result data={patch.data} error={patch.error} loading={patch.loading} />
        <Result data={del.data} error={del.error} loading={del.loading} />
      </Section>

      <Section title="예약 (Booking) — 위 skill_item_id 사용">
        <p style={{ fontSize: 13 }}>
          예약 생성 = 낙찰. buyer 포인트가 amount 만큼 차감되어 에스크로에 보관됩니다.
        </p>
        <Field label="buyer_id" value={buyerId} onChange={(e) => setBuyerId(e.target.value)} />
        <Field
          label="amount (낙찰가)"
          type="number"
          value={bookingAmount}
          onChange={(e) => setBookingAmount(e.target.value)}
        />
        <Field
          label="scheduled_at"
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
        />
        <button onClick={() => createBooking.run()}>POST /skill-bookings (판매자)</button>
        <button onClick={() => myBookings.run()}>GET /skill-bookings (인증)</button>
        <Result data={createBooking.data} error={createBooking.error} loading={createBooking.loading} />
        <Result data={myBookings.data} error={myBookings.error} loading={myBookings.loading} />
        <Field
          label="booking_id"
          value={bookingId}
          onChange={(e) => setBookingId(e.target.value)}
        />
        <Field
          label="scheduled_at 변경용 status (참고용)"
          value={bookingStatus}
          onChange={(e) => setBookingStatus(e.target.value)}
        />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
          <button onClick={() => getBooking.run()}>GET</button>
          <button onClick={() => patchBooking.run()}>PATCH (일정 변경)</button>
          <button onClick={() => completeBooking.run()}>
            POST /complete (구매자, 정산)
          </button>
          <button onClick={() => cancelBooking.run()}>DELETE (취소·환불)</button>
        </div>
        <Field
          label="no-show party (seller/buyer)"
          value={noShowParty}
          onChange={(e) => setNoShowParty(e.target.value)}
        />
        <button onClick={() => noShowBooking.run()}>POST /no-show</button>
        <Result data={getBooking.data} error={getBooking.error} loading={getBooking.loading} />
        <Result data={patchBooking.data} error={patchBooking.error} loading={patchBooking.loading} />
        <Result data={completeBooking.data} error={completeBooking.error} loading={completeBooking.loading} />
        <Result data={cancelBooking.data} error={cancelBooking.error} loading={cancelBooking.loading} />
        <Result data={noShowBooking.data} error={noShowBooking.error} loading={noShowBooking.loading} />
      </Section>

      <Section title="에스크로 (Escrow)">
        <Field
          label="booking_id (선택)"
          value={escrowBookingId}
          onChange={(e) => setEscrowBookingId(e.target.value)}
        />
        <Field
          label="payee_id"
          value={escrowPayeeId}
          onChange={(e) => setEscrowPayeeId(e.target.value)}
        />
        <Field
          label="amount"
          type="number"
          value={escrowAmount}
          onChange={(e) => setEscrowAmount(e.target.value)}
        />
        <button onClick={() => createEscrow.run()}>POST /escrows (인증)</button>
        <Result data={createEscrow.data} error={createEscrow.error} loading={createEscrow.loading} />
        <Field
          label="escrow_id"
          value={escrowId}
          onChange={(e) => setEscrowId(e.target.value)}
        />
        <Field
          label="status (holding/settled/refunded)"
          value={escrowStatus}
          onChange={(e) => setEscrowStatus(e.target.value)}
        />
        <button onClick={() => getEscrow.run()}>GET</button>
        <button onClick={() => patchEscrow.run()}>PATCH status</button>
        <Result data={getEscrow.data} error={getEscrow.error} loading={getEscrow.loading} />
        <Result data={patchEscrow.data} error={patchEscrow.error} loading={patchEscrow.loading} />
      </Section>
    </div>
  );
}
