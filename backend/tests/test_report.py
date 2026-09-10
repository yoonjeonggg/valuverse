"""신고 접수 검증 + 어뷰징 처리 연동 테스트 (FR-COM-04)."""

from datetime import timedelta

from app.core.config import settings
from app.core.timeutils import now


def _item(client, headers):
    return client.post(
        "/items",
        json={
            "title": "신고 대상 상품",
            "start_price": 1000,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    ).json()


def _report(client, headers, target_type, target_id, reason="어뷰징"):
    return client.post(
        "/reports",
        json={"target_type": target_type, "target_id": target_id, "reason": reason},
        headers=headers,
    )


def _notif_types(client, headers):
    return [
        n["type"]
        for n in client.get("/users/me/notifications", headers=headers).json()
    ]


# ---------- 접수 검증 ----------
def test_report_unknown_target_404(client, make_user):
    h, _ = make_user()
    assert _report(client, h, "item", 999).status_code == 404


def test_cannot_report_self(client, make_user):
    h, user = make_user()
    assert _report(client, h, "user", user["id"]).status_code == 400


def test_duplicate_open_report_conflicts(client, make_user):
    reporter_h, _ = make_user()
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    assert _report(client, reporter_h, "item", item["id"]).status_code == 201
    assert _report(client, reporter_h, "item", item["id"]).status_code == 409


def test_new_report_notifies_admin(client, make_user):
    admin_h, _ = make_user(admin=True)
    reporter_h, _ = make_user()
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    _report(client, reporter_h, "item", item["id"])
    assert "report_new" in _notif_types(client, admin_h)


# ---------- 처리 연동 ----------
def test_resolve_item_report_soft_deletes_item(client, make_user):
    admin_h, _ = make_user(admin=True)
    reporter_h, _ = make_user()
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    rep = _report(client, reporter_h, "item", item["id"]).json()

    r = client.patch(
        f"/reports/{rep['id']}", json={"status": "resolved"}, headers=admin_h
    )
    assert r.status_code == 200

    assert client.get(f"/items/{item['id']}").status_code == 404
    assert "report_resolved" in _notif_types(client, reporter_h)
    assert "sanction" in _notif_types(client, seller_h)


def test_resolve_review_report_deletes_and_recalcs_rating(client, make_user):
    admin_h, _ = make_user(admin=True)
    reporter_h, _ = make_user()
    author_h, author = make_user()
    target_h, target = make_user()

    item = _item(client, target_h)
    resp = client.post(
        "/reviews",
        json={
            "target_user_id": target["id"],
            "item_id": item["id"],
            "rating": 1,
            "content": "허위",
        },
        headers=author_h,
    )
    assert resp.status_code == 201, resp.text
    rv = resp.json()
    assert client.get(f"/users/{target['id']}").json()["rating"] == 1.0

    rep = _report(client, reporter_h, "review", rv["id"]).json()
    client.patch(
        f"/reports/{rep['id']}", json={"status": "resolved"}, headers=admin_h
    )

    assert client.get(f"/users/{target['id']}").json()["rating"] == 0.0
    assert "sanction" in _notif_types(client, author_h)


def test_resolve_user_reports_auto_deactivate(client, make_user):
    admin_h, _ = make_user(admin=True)
    bad_h, bad = make_user()

    for _ in range(settings.report_auto_deactivate_threshold):
        rh, _ = make_user()
        rep = _report(client, rh, "user", bad["id"]).json()
        client.patch(
            f"/reports/{rep['id']}", json={"status": "resolved"}, headers=admin_h
        )

    # 비활성화되어 로그인/조회 불가
    me = client.get("/users/me", headers=bad_h)
    assert me.status_code == 403


def test_reject_report_applies_no_sanction(client, make_user):
    admin_h, _ = make_user(admin=True)
    reporter_h, _ = make_user()
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    rep = _report(client, reporter_h, "item", item["id"]).json()

    client.patch(
        f"/reports/{rep['id']}", json={"status": "rejected"}, headers=admin_h
    )
    assert client.get(f"/items/{item['id']}").status_code == 200
    assert "report_rejected" in _notif_types(client, reporter_h)


def test_resolve_twice_does_not_double_sanction(client, make_user):
    admin_h, _ = make_user(admin=True)
    bad_h, bad = make_user()
    rh, _ = make_user()
    rep = _report(client, rh, "user", bad["id"]).json()

    for _ in range(3):
        client.patch(
            f"/reports/{rep['id']}", json={"status": "resolved"}, headers=admin_h
        )
    # 같은 신고 1건만 resolved 이므로 임계치(3) 미달 → 계정 유지
    assert client.get("/users/me", headers=bad_h).status_code == 200


# ---------- 조회 필터 ----------
def test_list_reports_filter_by_target(client, make_user):
    admin_h, _ = make_user(admin=True)
    r1_h, _ = make_user()
    s_h, _ = make_user()
    item = _item(client, s_h)
    _report(client, r1_h, "item", item["id"])

    rows = client.get(
        f"/reports?target_type=item&target_id={item['id']}", headers=admin_h
    ).json()
    assert len(rows) == 1
    assert rows[0]["target_id"] == item["id"]


def test_list_reports_requires_admin(client, make_user):
    h, _ = make_user()
    assert client.get("/reports", headers=h).status_code == 403
