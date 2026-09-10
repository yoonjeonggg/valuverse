from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 보안 - 운영 환경에서는 반드시 .env 로 재정의할 것
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # DB
    database_url: str = "sqlite:///./auction.db"
    # True 면 앱 시작 시 테이블을 자동 생성한다(마이그레이션 없이 빠른 실행용).
    # 운영/마이그레이션 사용 시 False 로 두고 `alembic upgrade head` 를 쓴다.
    auto_create_tables: bool = True

    # Redis (실시간 순위/캐시용, 현재 미사용 - 예약)
    redis_url: str = "redis://localhost:6379/0"

    # 경매 - 마감 임박 입찰 시 자동 연장 (스나이핑 방지, FR-AUC-03)
    auction_extend_window_seconds: int = 180
    auction_extend_by_seconds: int = 180
    auction_max_extensions: int = 10

    # 포인트 이코노미 (FR-PRD-05~08)
    point_checkin_base: int = 10          # 출석 기본 지급
    point_checkin_streak_bonus: int = 2   # 연속 출석 1일당 추가 (상한 아래)
    point_checkin_streak_cap: int = 7     # 보너스가 붙는 최대 연속일수
    point_ad_reward: int = 5              # 광고 1회 시청 지급
    point_ad_daily_limit: int = 5         # 하루 광고 보상 횟수 상한
    spotlight_cost: int = 100             # 상단 노출권 가격
    spotlight_hours: int = 24             # 상단 노출 지속 시간
    coupon_valid_days: int = 30           # 교환한 쿠폰 유효기간(일)

    # 신고 - 처리 완료된 신고가 이 수 이상 쌓이면 대상 계정을 자동 비활성화
    report_auto_deactivate_threshold: int = 3

    # CORS - 프론트엔드 오리진. 쉼표로 구분. 운영에서는 .env 로 재정의할 것
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
