from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["Review"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: DbSession, user: CurrentUser):
    return review_service.create_review(db, user, payload)


@router.get("", response_model=list[ReviewResponse])
def list_reviews(
    db: DbSession,
    target_user_id: int | None = None,
    item_id: int | None = None,
    skill_item_id: int | None = None,
):
    return review_service.list_reviews(db, target_user_id, item_id, skill_item_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    db: DbSession,
    user: CurrentUser,
):
    return review_service.update_review(db, review_id, user, payload)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: DbSession, user: CurrentUser):
    review_service.delete_review(db, review_id, user)
