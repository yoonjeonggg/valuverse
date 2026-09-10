from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.timeutils import now, aware
from app.models.auction import Item
from app.models.review import Review
from app.models.skill import SkillBooking, SkillItem
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewUpdate

# 작성 후 수정 가능 기간(일)
EDIT_WINDOW_DAYS = 7


def _assert_traded(
    db: Session, author_id: int, target_id: int, payload: ReviewCreate
) -> None:
    """작성자와 대상이 완료된 거래로 엮여 있는지 검증한다 (일반/스킬)."""
    if payload.item_id:
        item = db.get(Item, payload.item_id)
        if not item or item.status != "closed" or not item.winner_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "낙찰이 완료된 거래에만 리뷰를 남길 수 있습니다."
            )
        parties = {item.seller_id, item.winner_id}
        if author_id not in parties or target_id not in parties:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "해당 거래의 당사자만 리뷰를 남길 수 있습니다."
            )
        dup_col = Review.item_id == payload.item_id
    else:
        booking = (
            db.query(SkillBooking)
            .filter(
                SkillBooking.skill_item_id == payload.skill_item_id,
                SkillBooking.status == "completed",
            )
            .first()
        )
        if not booking:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "완료된 스킬 거래에만 리뷰를 남길 수 있습니다."
            )
        parties = {booking.seller_id, booking.buyer_id}
        if author_id not in parties or target_id not in parties:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "해당 거래의 당사자만 리뷰를 남길 수 있습니다."
            )
        dup_col = Review.skill_item_id == payload.skill_item_id

    dup = (
        db.query(Review.id)
        .filter(Review.author_id == author_id, dup_col, Review.is_deleted.is_(False))
        .first()
    )
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 이 거래에 리뷰를 남겼습니다.")


def _recalc_rating(db: Session, target_user_id: int) -> None:
    avg = (
        db.query(func.avg(Review.rating))
        .filter(
            Review.target_user_id == target_user_id,
            Review.is_deleted.is_(False),
        )
        .scalar()
    )
    user = db.query(User).filter(User.id == target_user_id).first()
    if user:
        user.rating = round(float(avg), 2) if avg is not None else 0.0


def create_review(db: Session, author: User, payload: ReviewCreate) -> Review:
    if payload.target_user_id == author.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인에게 리뷰를 남길 수 없습니다.")
    if not db.query(User.id).filter(User.id == payload.target_user_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "대상 사용자를 찾을 수 없습니다.")

    _assert_traded(db, author.id, payload.target_user_id, payload)

    review = Review(
        author_id=author.id,
        target_user_id=payload.target_user_id,
        item_id=payload.item_id,
        skill_item_id=payload.skill_item_id,
        rating=payload.rating,
        content=payload.content,
    )
    db.add(review)
    db.flush()
    _recalc_rating(db, payload.target_user_id)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(
    db: Session,
    target_user_id: int | None = None,
    item_id: int | None = None,
    skill_item_id: int | None = None,
) -> list[Review]:
    q = db.query(Review).filter(Review.is_deleted.is_(False))
    if target_user_id:
        q = q.filter(Review.target_user_id == target_user_id)
    if item_id:
        q = q.filter(Review.item_id == item_id)
    if skill_item_id:
        q = q.filter(Review.skill_item_id == skill_item_id)
    return q.order_by(Review.created_at.desc()).all()


def _get(db: Session, review_id: int) -> Review:
    review = (
        db.query(Review)
        .filter(Review.id == review_id, Review.is_deleted.is_(False))
        .first()
    )
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "리뷰를 찾을 수 없습니다.")
    return review


def update_review(
    db: Session, review_id: int, user: User, payload: ReviewUpdate
) -> Review:
    review = _get(db, review_id)
    if review.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 리뷰만 수정할 수 있습니다.")
    created = aware(review.created_at)
    if created is not None and (now() - created).days > EDIT_WINDOW_DAYS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"작성 후 {EDIT_WINDOW_DAYS}일이 지나 수정할 수 없습니다.",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.flush()
    _recalc_rating(db, review.target_user_id)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: int, user: User) -> None:
    review = _get(db, review_id)
    if review.author_id != user.id and not user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "본인 또는 관리자만 삭제할 수 있습니다."
        )
    review.is_deleted = True
    db.flush()
    _recalc_rating(db, review.target_user_id)
    db.commit()
