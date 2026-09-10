// datetime-local 입력값(로컬 시간)을 ISO 8601(UTC) 문자열로 변환.
export function toIso(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}
