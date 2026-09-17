"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

/* ---------- data-fetching hook ---------- */
export function useCall<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
) {
  const [data, setData] = useState<TResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(
    async (...args: TArgs) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn(...args);
        setData(result);
        return result;
      } catch (e) {
        const msg =
          e instanceof ApiError
            ? e.message
            : e instanceof Error
              ? e.message
              : String(e);
        setError(msg);
        setData(null);
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [fn],
  );

  return { data, error, loading, run, setData };
}

/* ---------- labelled input row ---------- */
export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}

/* ---------- consumer-facing card (Section 의 API 콘솔 스타일 대신) ---------- */
export function Card({
  title,
  eyebrow,
  right,
  children,
}: {
  title?: string;
  eyebrow?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="card">
      {(title || right) && (
        <div className="card__head">
          <div>
            {eyebrow && <div className="card__eyebrow">{eyebrow}</div>}
            {title && <h3>{title}</h3>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

/* ---------- live countdown chip ---------- */
export function Countdown({ endTime }: { endTime: string | null | undefined }) {
  const [ms, setMs] = useState<number | null>(() =>
    endTime ? new Date(endTime).getTime() - Date.now() : null,
  );

  useEffect(() => {
    if (!endTime) return;
    const target = new Date(endTime).getTime();
    const id = setInterval(() => setMs(target - Date.now()), 1000);
    return () => clearInterval(id);
  }, [endTime]);

  if (!endTime || ms === null) return null;
  if (ms <= 0)
    return (
      <span className="countdown urgent">
        <Icon name="clock" size={14} /> 마감
      </span>
    );

  const totalSec = Math.floor(ms / 1000);
  const d = Math.floor(totalSec / 86400);
  const h = Math.floor((totalSec % 86400) / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const label =
    d > 0 ? `${d}일 ${h}시간 남음` : h > 0 ? `${h}시간 ${m}분 남음` : `${m}분 ${s}초 남음`;
  const urgent = ms <= 5 * 60 * 1000;

  return (
    <span className={"countdown" + (urgent ? " urgent" : "")}>
      <Icon name="clock" size={14} /> {label}
    </span>
  );
}

/* ---------- page header ---------- */
export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-head">
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h1>{title}</h1>
      {children}
    </header>
  );
}

/* ---------- inline icon set (SVG, not emoji) ---------- */
const PATHS: Record<string, React.ReactNode> = {
  gavel: (
    <>
      <path d="m14 4 6 6-3 3-6-6z" />
      <path d="m8 10 6 6" />
      <path d="m5 13 5 5-2 2-5-5z" />
      <path d="M4 21h9" />
    </>
  ),
  bolt: <path d="M13 2 4 14h7l-1 8 9-12h-7z" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  bell: (
    <>
      <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </>
  ),
  coin: (
    <>
      <ellipse cx="12" cy="7" rx="7" ry="3" />
      <path d="M5 7v6c0 1.7 3.1 3 7 3s7-1.3 7-3V7" />
      <path d="M5 13v4c0 1.7 3.1 3 7 3s7-1.3 7-3v-4" />
    </>
  ),
  shield: <path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z" />,
  spark: (
    <>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="m6 6 2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
    </>
  ),
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  chat: (
    <>
      <path d="M4 5h16v11H9l-4 4v-4H4z" />
      <path d="M8 9h8M8 12h5" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6 6 18" />,
};

export function Icon({
  name,
  size = 18,
}: {
  name: keyof typeof PATHS;
  size?: number;
}) {
  return (
    <svg
      className="icon"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
