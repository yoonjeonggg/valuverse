"""응답의 날짜가 항상 타임존을 포함한 UTC 로 나가는지 확인한다.

SQLite 는 tzinfo 를 저장하지 않아 "2026-11-12T06:20:00" 처럼 타임존 없이 응답했고,
브라우저가 이를 로컬 시각으로 읽어 KST 에서 마감·예약 시간이 9시간 어긋났다.
"""

from datetime import UTC, datetime, timedelta, timezone

from app.core.timeutils import now
from tests.conftest import create_skill

KST = timezone(timedelta(hours=9))


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, f"타임존 없는 응답: {value}"
    return parsed


def test_offset_input_is_stored_and_returned_as_same_instant(client, make_user):
    h, _ = make_user()
    end_kst = (now() + timedelta(days=1)).astimezone(KST).replace(microsecond=0)

    created = create_skill(client, h, end_time=end_kst.isoformat())
    fetched = client.get(f"/skill-items/{created['id']}").json()

    for row in (created, fetched):
        end = _parse(row["end_time"])
        assert end.utcoffset() == timedelta(0)
        assert end == end_kst
        _parse(row["created_at"])


def test_listed_items_and_bids_have_timezone(client, make_user, set_points):
    seller, _ = make_user()
    buyer, buyer_user = make_user()
    set_points(buyer_user["id"], 10_000)
    skill = create_skill(client, seller)
    client.post(f"/skill-items/{skill['id']}/bids", json={"amount": 3000}, headers=buyer)

    for row in client.get("/skill-items").json():
        _parse(row["end_time"])
    for bid in client.get(f"/skill-items/{skill['id']}/bids").json():
        assert _parse(bid["created_at"]) <= datetime.now(UTC)
