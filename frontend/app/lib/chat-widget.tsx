"use client";

import { useState } from "react";
import { api } from "./api";
import { Icon } from "./ui";

type ChatMessage = {
  role: "user" | "bot";
  text: string;
  references?: string[];
};

type ChatResponse = { answer: string; references: string[]; item_id: number | null };

const GREETING: ChatMessage = {
  role: "bot",
  text: "안녕하세요! 입찰 방식, 마감/자동연장, 즉시구매, 에스크로/정산 등 궁금한 점을 물어보세요.",
};

/** 상품 상세 화면 진입점 AI 챗봇(입찰 상담) - 디자인 요구사항 명세서 4.7 */
export function ChatWidget({
  itemId,
  itemType = "item",
}: {
  itemId?: number;
  itemType?: "item" | "skill_item";
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [loading, setLoading] = useState(false);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api<ChatResponse>("/ai/chat", {
        method: "POST",
        body: { message: text, item_id: itemId, item_type: itemType },
      });
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: res.answer, references: res.references },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "일시적인 오류로 답변을 가져오지 못했습니다. 다시 시도해 주세요." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-panel" role="dialog" aria-label="AI 입찰 상담">
          <div className="chat-panel__head">
            <span>
              <Icon name="chat" size={16} /> AI 입찰 상담
            </span>
            <button
              className="btn-ghost btn-sm"
              onClick={() => setOpen(false)}
              aria-label="닫기"
            >
              <Icon name="close" size={14} />
            </button>
          </div>
          <div className="chat-log">
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg chat-msg--${m.role}`}>
                <p>{m.text}</p>
                {m.references && m.references.length > 0 && (
                  <div className="chat-refs">
                    {m.references.map((r) => (
                      <span key={r} className="badge badge--red">
                        {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="chat-msg chat-msg--bot">
                <p>답변 작성 중…</p>
              </div>
            )}
          </div>
          <div className="chat-input">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") send();
              }}
              placeholder="궁금한 점을 입력하세요"
              aria-label="상담 메시지 입력"
            />
            <button
              className="btn btn-primary btn-sm"
              onClick={send}
              disabled={loading || !input.trim()}
            >
              전송
            </button>
          </div>
        </div>
      )}
      <button
        className="chat-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "AI 입찰 상담 닫기" : "AI 입찰 상담 열기"}
      >
        <Icon name={open ? "close" : "chat"} size={20} />
      </button>
    </div>
  );
}
