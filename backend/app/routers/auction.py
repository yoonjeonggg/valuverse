from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.schemas.auction import (
    BidCreate,
    BidResponse,
    BlindBidCreate,
    BlindBidRankResponse,
    BlindBidResultRow,
    BuyNowResponse,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.schemas.point import SpotlightResponse
from app.services import auction_service

item_router = APIRouter(prefix="/items", tags=["Item / Auction"])
bid_router = APIRouter(tags=["Bid"])


# ==================== Item ====================
@item_router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: DbSession, user: CurrentUser):
    return auction_service.create_item(db, user.id, payload)


@item_router.get("", response_model=list[ItemResponse])
def list_items(
    db: DbSession,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    ids: Annotated[list[int] | None, Query(max_length=200)] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """`ids` 를 주면 그 상품들만 돌려준다 (마이페이지처럼 여러 상품을 한 번에 조회할 때)."""
    return auction_service.list_items(db, category, status_filter, skip, limit, ids)


@item_router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: DbSession):
    return auction_service.get_item(db, item_id)


@item_router.patch("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdate, db: DbSession, user: CurrentUser):
    return auction_service.update_item(db, item_id, user.id, payload)


@item_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: DbSession, user: CurrentUser):
    auction_service.delete_item(db, item_id, user.id)


@item_router.post("/{item_id}/close", response_model=ItemResponse)
def close_item(item_id: int, db: DbSession, user: CurrentUser):
    return auction_service.close_item(db, item_id, user.id)


@item_router.post("/{item_id}/buy-now", response_model=BuyNowResponse)
def buy_now(item_id: int, db: DbSession, user: CurrentUser):
    item = auction_service.buy_now(db, item_id, user.id)
    return BuyNowResponse(
        item_id=item.id,
        buyer_id=user.id,
        final_price=item.final_price,
        status=item.status,
    )


@item_router.post("/{item_id}/spotlight", response_model=SpotlightResponse)
def buy_spotlight(item_id: int, db: DbSession, user: CurrentUser):
    item = auction_service.buy_spotlight(db, item_id, user)
    return SpotlightResponse(
        item_id=item.id,
        spotlight_until=item.spotlight_until,
        cost=settings.spotlight_cost,
        balance=user.points,
    )


# ==================== Bid ====================
@item_router.post(
    "/{item_id}/bids", response_model=BidResponse, status_code=status.HTTP_201_CREATED
)
def create_bid(item_id: int, payload: BidCreate, db: DbSession, user: CurrentUser):
    return auction_service.create_bid(db, item_id, user.id, payload)


@item_router.get("/{item_id}/bids", response_model=list[BidResponse])
def list_item_bids(item_id: int, db: DbSession):
    return auction_service.list_bids_for_item(db, item_id)


@bid_router.get("/users/me/bids", response_model=list[BidResponse], tags=["Bid"])
def list_my_bids(db: DbSession, user: CurrentUser):
    return auction_service.list_my_bids(db, user.id)


@bid_router.delete(
    "/bids/{bid_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Bid"]
)
def cancel_bid(bid_id: int, db: DbSession, user: CurrentUser):
    auction_service.cancel_bid(db, bid_id, user.id)


# ==================== Blind Bid ====================
@item_router.post(
    "/{item_id}/blind-bids",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    tags=["Blind Bid"],
)
def create_blind_bid(
    item_id: int,
    payload: BlindBidCreate,
    db: DbSession,
    user: CurrentUser,
):
    bid = auction_service.create_blind_bid(db, item_id, user.id, payload)
    return {"id": bid.id, "item_id": bid.item_id, "message": "입찰이 접수되었습니다."}


@item_router.get(
    "/{item_id}/blind-bids/my-rank",
    response_model=BlindBidRankResponse,
    tags=["Blind Bid"],
)
def get_my_blind_rank(item_id: int, db: DbSession, user: CurrentUser):
    return auction_service.get_my_blind_rank(db, item_id, user.id)


@item_router.get(
    "/{item_id}/blind-bids/results",
    response_model=list[BlindBidResultRow],
    tags=["Blind Bid"],
)
def get_blind_results(item_id: int, db: DbSession):
    return auction_service.get_blind_results(db, item_id)


@bid_router.delete(
    "/blind-bids/{bid_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Blind Bid"],
)
def cancel_blind_bid(bid_id: int, db: DbSession, user: CurrentUser):
    auction_service.cancel_blind_bid(db, bid_id, user.id)
