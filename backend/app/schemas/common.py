from pydantic import BaseModel, ConfigDict, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def reject_null(*fields: str):
    """PATCH 스키마용: 필드를 생략하면 '변경 없음'이지만, 명시적 null 은 NOT NULL 컬럼에
    그대로 들어가 500 이 났다. 지정한 필드의 null 을 422 로 막는다.

        class ItemUpdate(BaseModel):
            title: str | None = None
            _not_null = reject_null("title")
    """

    def _check(cls, value):
        if value is None:
            raise ValueError("null 로 비울 수 없는 항목입니다.")
        return value

    return field_validator(*fields)(_check)
