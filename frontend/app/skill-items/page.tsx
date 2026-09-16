"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { toIso } from "../lib/format";
import { Field, PageHeader, Result, Section, useCall } from "../lib/ui";

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

  const [introText, setIntroText] = useState("");
  const skillTag = useCall(() =>
    api("/ai/skill-tag-suggestion", {
      method: "POST",
      auth: true,
      body: { intro_text: introText },
    }),
  );

  return (
    <div>
      <PageHeader eyebrow="Skill Auction" title="스킬 경매">
        <p>
          무형의 재능을 거래합니다. 예약 생성이 곧 낙찰이며, 낙찰금은
          에스크로에 보관됐다가 완료·노쇼에 따라 정산·환불됩니다.
        </p>
      </PageHeader>

      <Section title="스킬 상품 목록" method="GET /skill-items">
        <Field label="category" value={category} onChange={(e) => setCategory(e.target.value)} />
        <Field
          label="status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => list.run()}>목록 조회</button>
        </div>
        <Result {...list} />
      </Section>

      <Section title="스킬 상품 등록" method="POST /skill-items">
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
        <div className="actions">
          <button className="btn-primary" onClick={() => create.run()}>
            등록
          </button>
        </div>
        <Result {...create} />
      </Section>

      <Section title="대상 스킬 상품 선택" method="GET · PATCH · DELETE /skill-items/{id}">
        <Field
          label="skill_item_id"
          value={skillItemId}
          onChange={(e) => setSkillItemId(e.target.value)}
        />
        <Field
          label="patch title"
          value={patchTitle}
          onChange={(e) => setPatchTitle(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => getOne.run()}>조회</button>
          <button onClick={() => patch.run()}>제목 수정</button>
          <button onClick={() => del.run()}>삭제</button>
        </div>
        <Result {...getOne} />
        <Result {...patch} />
        <Result {...del} />
      </Section>

      <Section title="예약 · 정산" method="POST /skill-bookings · /complete · /no-show">
        <p className="hint">
          예약 생성 = 낙찰. 구매자 포인트가 amount 만큼 차감되어 에스크로에
          보관됩니다.
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
        <div className="actions">
          <button className="btn-primary" onClick={() => createBooking.run()}>
            예약 생성 (판매자)
          </button>
          <button onClick={() => myBookings.run()}>내 예약</button>
        </div>
        <Result {...createBooking} />
        <Result {...myBookings} />
        <Field
          label="booking_id"
          value={bookingId}
          onChange={(e) => setBookingId(e.target.value)}
        />
        <Field
          label="일정 변경용 status"
          value={bookingStatus}
          onChange={(e) => setBookingStatus(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => getBooking.run()}>조회</button>
          <button onClick={() => patchBooking.run()}>일정 변경</button>
          <button onClick={() => completeBooking.run()}>완료 (구매자, 정산)</button>
          <button onClick={() => cancelBooking.run()}>취소 · 환불</button>
        </div>
        <Field
          label="노쇼 당사자 (seller/buyer)"
          value={noShowParty}
          onChange={(e) => setNoShowParty(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => noShowBooking.run()}>노쇼 처리</button>
        </div>
        <Result {...getBooking} />
        <Result {...patchBooking} />
        <Result {...completeBooking} />
        <Result {...cancelBooking} />
        <Result {...noShowBooking} />
      </Section>

      <Section title="에스크로" method="POST · GET · PATCH /escrows">
        <p className="hint">
          상태 변경(PATCH)은 실제 포인트 이동을 동반합니다 —
          settled=판매자 정산, refunded=구매자 환불.
        </p>
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
        <div className="actions">
          <button onClick={() => createEscrow.run()}>에스크로 생성</button>
        </div>
        <Result {...createEscrow} />
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
        <div className="actions">
          <button onClick={() => getEscrow.run()}>조회</button>
          <button onClick={() => patchEscrow.run()}>상태 변경</button>
        </div>
        <Result {...getEscrow} />
        <Result {...patchEscrow} />
      </Section>

      <Section title="AI 보조 - 소개글 태깅" method="POST /ai/skill-tag-suggestion">
        <p className="hint">
          소개글의 키워드를 분석해 카테고리·난이도를 제안합니다(LLM 없이 규칙 기반).
        </p>
        <Field
          label="소개글"
          value={introText}
          onChange={(e) => setIntroText(e.target.value)}
        />
        <div className="actions">
          <button onClick={() => skillTag.run()}>카테고리/난이도 태깅</button>
        </div>
        <Result {...skillTag} />
      </Section>
    </div>
  );
}
