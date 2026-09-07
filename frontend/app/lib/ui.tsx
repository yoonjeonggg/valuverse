"use client";

// 연동 확인용 최소 UI 헬퍼. 스타일은 의도적으로 최소화.

import { useCallback, useState } from "react";
import { ApiError } from "./api";

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

export function Result({
  data,
  error,
  loading,
}: {
  data: unknown;
  error?: string | null;
  loading?: boolean;
}) {
  return (
    <div style={{ marginTop: 8 }}>
      {loading && <p>로딩 중…</p>}
      {error && (
        <pre style={{ color: "crimson", whiteSpace: "pre-wrap" }}>{error}</pre>
      )}
      {data !== null && data !== undefined && (
        <pre
          style={{
            background: "#f4f4f4",
            color: "#111",
            padding: 8,
            overflowX: "auto",
            fontSize: 12,
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label style={{ display: "block", margin: "4px 0" }}>
      <span style={{ display: "inline-block", minWidth: 160 }}>{label}</span>
      <input {...props} style={{ padding: 4, minWidth: 240 }} />
    </label>
  );
}

export function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      style={{
        border: "1px solid #ccc",
        padding: 12,
        margin: "12px 0",
      }}
    >
      <h3 style={{ margin: "0 0 8px" }}>{title}</h3>
      {children}
    </section>
  );
}
