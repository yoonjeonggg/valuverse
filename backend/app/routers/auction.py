from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auction import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    BidCreate,
    BidResponse,
    BlindBidCreate,
    BlindBidRankResponse,
    BlindBidResultRow,
)
from app.services import auction_service

item_router = APIRouter(prefix="/items", tags=["Item / Auction"])
bid_router = APIRouter(tags=["Bid"])


# ==================== Item ====================
@item_router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return auction_service.create_item(db, user.id, payload)


@item_router.get("", response_model=list[ItemResponse])
def list_items(
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    return auction_service.list_items(db, category, status_filter, skip, limit)


@item_router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return auction_service.get_item(db, item_id)


@item_router.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return auction_service.update_item(db, item_id, user.id, payload)


@item_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    auction_service.delete_item(db, item_id, user.id)


# ==================== Bid ====================
@item_router.post(
    "/{item_id}/bids", response_model=BidResponse, status_code=status.HTTP_201_CREATED
)
def create_bid(
    item_id: int,
    payload: BidCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return auction_service.create_bid(db, item_id, user.id, payload)


@item_router.get("/{item_id}/bids", response_model=list[BidResponse])
def list_item_bids(item_id: int, db: Session = Depends(get_db)):
    return auction_service.list_bids_for_item(db, item_id)


@bid_router.get("/users/me/bids", response_model=list[BidResponse], tags=["Bid"])
def list_my_bids(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return auction_service.list_my_bids(db, user.id)


@bid_router.delete(
    "/bids/{bid_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Bid"]
)
def cancel_bid(
    bid_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bid = auction_service.create_blind_bid(db, item_id, user.id, payload)
    return {"id": bid.id, "item_id": bid.item_id, "message": "입찰이 접수되었습니다."}


@item_router.get(
    "/{item_id}/blind-bids/my-rank",
    response_model=BlindBidRankResponse,
    tags=["Blind Bid"],
)
def get_my_blind_rank(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return auction_service.get_my_blind_rank(db, item_id, user.id)


@item_router.get(
    "/{item_id}/blind-bids/results",
    response_model=list[BlindBidResultRow],
    tags=["Blind Bid"],
)
def get_blind_results(item_id: int, db: Session = Depends(get_db)):
    return auction_service.get_blind_results(db, item_id)


@bid_router.delete(
    "/blind-bids/{bid_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Blind Bid"],
)
def cancel_blind_bid(
    bid_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    auction_service.cancel_blind_bid(db, bid_id, user.id)
