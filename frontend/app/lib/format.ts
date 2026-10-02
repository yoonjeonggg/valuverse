// datetime-local 입력값(로컬 시간)을 ISO 8601(UTC) 문자열로 변환.
export function toIso(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}

// 서버(컨테이너는 UTC)와 브라우저가 같은 문자열을 만들도록 표시 시간대를 고정한다.
// 서버 렌더 결과와 다르면 hydration 경고가 나고 화면이 한 번 바뀐다.
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDateTime(iso: string): string {
  return DATE_TIME_FORMAT.format(new Date(iso));
}
