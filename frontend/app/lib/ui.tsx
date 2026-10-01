"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./api";

/* ---------- data-fetching hook ---------- */
export function useCall<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
) {
  const [data, setData] = useState<TResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // 호출부가 매 렌더마다 새 화살표 함수를 넘기므로 ref 로 최신 fn 을 들고 있고,
  // run 자체는 렌더 간에 동일한 참조로 유지한다 (effect 의존성 등에 안전).
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });

  const run = useCallback(
    async (...args: TArgs) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fnRef.current(...args);
        setData(result);
        return result;
      } catch (e) {
        setError(errorMessage(e));
        setData(null);
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [],
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

/* ---------- labelled select row ---------- */
export function SelectField({
  label,
  options,
  ...props
}: {
  label: string;
  options: [value: string, label: string][];
} & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="field">
      <span>{label}</span>
      <select {...props}>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

/* ---------- 요청 실패 메시지 (없으면 아무것도 그리지 않는다) ---------- */
export function ErrorText({
  error,
  notice = false,
}: {
  error: string | null;
  notice?: boolean;
}) {
  if (!error) return null;
  return <p className={notice ? "notice notice--error" : "hint hint--error"}>{error}</p>;
}

/* ---------- 섹션 카드 ---------- */
export function Card({
  title,
  right,
  children,
}: {
  title?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="card">
      {(title || right) && (
        <div className="card__head">
          <div>{title && <h3>{title}</h3>}</div>
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
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-head">
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
  back: <path d="M19 12H5M11 6l-6 6 6 6" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </>
  ),
  moon: <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 6.8 6.8 0 0 0 20 14.5z" />,
  chat: (
    <>
      <path d="M4 5h16v11H9l-4 4v-4H4z" />
      <path d="M8 9h8M8 12h5" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6 6 18" />,
  check: <path d="m5 12.5 4.5 4.5L19 7" />,
  calendar: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M4 10h16M9 3v4M15 3v4" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="0.8" />
    </>
  ),
  play: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m10 9 5 3-5 3z" />
    </>
  ),
  ticket: (
    <>
      <path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z" />
      <path d="M14 7v2M14 11v2M14 15v2" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  box: (
    <>
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z" />
      <path d="m4 7.5 8 4.5 8-4.5M12 12v9" />
    </>
  ),
  pen: (
    <>
      <path d="m15 5 4 4L9 19H5v-4z" />
      <path d="m13 7 4 4" />
    </>
  ),
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
