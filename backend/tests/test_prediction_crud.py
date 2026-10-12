"""예측 명제 수정/삭제와 베팅 취소의 예외 경로 테스트."""

from tests.conftest import in_days


def _bet(client, pred_id, headers, position="yes", amount=100):
    return client.post(
        f"/predictions/{pred_id}/bets",
        json={"position": position, "amount": amount},
        headers=headers,
    )


# ---------- 생성/조회 ----------
def test_create_prediction_requires_admin(client, make_user):
    h, _ = make_user()
    r = client.post("/predictions", json={"title": "x", "end_time": in_days(1)}, headers=h)
    assert r.status_code == 403


def test_create_prediction_rejects_past_end_time(client, make_user):
    admin_h, _ = make_user(admin=True)
    r = client.post("/predictions", json={"title": "x", "end_time": in_days(-1)}, headers=admin_h)
    assert r.status_code == 400


def test_get_missing_prediction_is_404(client):
    assert client.get("/predictions/999").status_code == 404
    assert client.get("/predictions/999/odds").status_code == 404


def test_list_predictions_filters_by_status(client, make_user, make_prediction, move_pred):
    admin_h, _ = make_user(admin=True)
    open_p = make_prediction(admin_h, title="열림")
    closed_p = make_prediction(admin_h, title="닫힘")
    client.patch(f"/predictions/{closed_p['id']}", json={"status": "closed"}, headers=admin_h)

    ongoing = client.get("/predictions?status=ongoing").json()
    assert [p["id"] for p in ongoing] == [open_p["id"]]
    assert len(client.get("/predictions").json()) == 2


# ---------- 수정 ----------
def test_admin_updates_open_prediction(client, make_user, make_prediction):
    admin_h, _ = make_user(admin=True)
    p = make_prediction(admin_h)
    r = client.patch(f"/predictions/{p['id']}", json={"title": "새 제목"}, headers=admin_h)
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "새 제목"


def test_non_admin_cannot_update_prediction(client, make_user, make_prediction):
    admin_h, _ = make_user(admin=True)
    user_h, _ = make_user()
    p = make_prediction(admin_h)
    assert (
        client.patch(f"/predictions/{p['id']}", json={"title": "x"}, headers=user_h).status_code
        == 403
    )


def test_closed_prediction_only_allows_status_change(client, make_user, make_prediction, move_pred):
    admin_h, _ = make_user(admin=True)
    p = make_prediction(admin_h)
    move_pred(p["id"], -10)

    r = client.patch(f"/predictions/{p['id']}", json={"title": "x"}, headers=admin_h)
    assert r.status_code == 409
    r = client.patch(f"/predictions/{p['id']}", json={"status": "closed"}, headers=admin_h)
    assert r.status_code == 200, r.text


def test_update_rejects_past_end_time(client, make_user, make_prediction):
    admin_h, _ = make_user(admin=True)
    p = make_prediction(admin_h)
    r = client.patch(f"/predictions/{p['id']}", json={"end_time": in_days(-1)}, headers=admin_h)
    assert r.status_code == 400


def test_settled_prediction_cannot_be_reopened(client, make_user, make_prediction, move_pred):
    """정산된 명제를 ongoing 으로 되돌리면 새 베팅을 받아 재정산될 수 있었다."""
    admin_h, _ = make_user(admin=True)
    p = make_prediction(admin_h)
    move_pred(p["id"], -10)
    settled = client.post(f"/predictions/{p['id']}/settle", json={"result": "yes"}, headers=admin_h)
    assert settled.status_code == 200, settled.text

    r = client.patch(f"/predictions/{p['id']}", json={"status": "ongoing"}, headers=admin_h)
    assert r.status_code == 409


# ---------- 삭제 ----------
def test_delete_prediction_without_bets(client, make_user, make_prediction):
    admin_h, _ = make_user(admin=True)
    p = make_prediction(admin_h)
    assert client.delete(f"/predictions/{p['id']}", headers=admin_h).status_code == 204
    assert client.get(f"/predictions/{p['id']}").status_code == 404


def test_delete_prediction_with_bets_conflicts(client, make_user, make_prediction, set_points):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 1000)
    p = make_prediction(admin_h)
    assert _bet(client, p["id"], user_h).status_code == 201
    assert client.delete(f"/predictions/{p['id']}", headers=admin_h).status_code == 409


# ---------- 베팅 ----------
def test_bet_on_closed_prediction_conflicts(
    client, make_user, make_prediction, set_points, move_pred
):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 1000)
    p = make_prediction(admin_h)
    move_pred(p["id"], -10)
    assert _bet(client, p["id"], user_h).status_code == 409


def test_bet_without_points_rejected(client, make_user, make_prediction, set_points):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 50)
    p = make_prediction(admin_h)
    assert _bet(client, p["id"], user_h, amount=100).status_code == 400


def test_cancel_bet_refunds_and_lists(client, make_user, make_prediction, set_points, get_points):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 1000)
    p = make_prediction(admin_h)
    bet = _bet(client, p["id"], user_h, amount=300).json()
    assert get_points(user_h) == 700

    assert client.delete(f"/prediction-bets/{bet['id']}", headers=user_h).status_code == 204
    assert get_points(user_h) == 1000
    mine = client.get("/users/me/prediction-bets", headers=user_h).json()
    assert mine[0]["is_cancelled"] is True
    assert mine[0]["result"] == "refunded"


def test_cancel_bet_twice_conflicts(client, make_user, make_prediction, set_points, get_points):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 1000)
    p = make_prediction(admin_h)
    bet = _bet(client, p["id"], user_h, amount=300).json()
    client.delete(f"/prediction-bets/{bet['id']}", headers=user_h)
    assert client.delete(f"/prediction-bets/{bet['id']}", headers=user_h).status_code == 409
    assert get_points(user_h) == 1000  # 이중 환불 없음


def test_cancel_bet_after_close_conflicts(
    client, make_user, make_prediction, set_points, move_pred
):
    admin_h, _ = make_user(admin=True)
    user_h, user = make_user()
    set_points(user["id"], 1000)
    p = make_prediction(admin_h)
    bet = _bet(client, p["id"], user_h).json()
    move_pred(p["id"], -10)
    assert client.delete(f"/prediction-bets/{bet['id']}", headers=user_h).status_code == 409
