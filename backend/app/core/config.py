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

    # Redis - 백엔드를 여러 대 띄울 때 WS 브로드캐스트를 인스턴스 간에 전달하는 데 쓴다.
    redis_url: str = "redis://localhost:6379/0"
    # memory: 단일 인스턴스(기본) / redis: 로드밸런싱 환경 (Redis pub/sub 로 전 인스턴스에 팬아웃)
    ws_broadcast_backend: str = "memory"

    # 경매 - 마감 임박 입찰 시 자동 연장 (스나이핑 방지, FR-AUC-03)
    auction_extend_window_seconds: int = 180
    auction_extend_by_seconds: int = 180
    auction_max_extensions: int = 10
    bid_cancel_window_seconds: int = 300  # 입찰 후 취소 가능 시간

    # 포인트 이코노미 (FR-PRD-05~08)
    point_checkin_base: int = 10          # 출석 기본 지급
    point_checkin_streak_bonus: int = 2   # 연속 출석 1일당 추가 (상한 아래)
    point_checkin_streak_cap: int = 7     # 보너스가 붙는 최대 연속일수
    point_ad_reward: int = 5              # 광고 1회 시청 지급
    point_ad_daily_limit: int = 5         # 하루 광고 보상 횟수 상한
    point_ad_min_interval_seconds: int = 30  # 광고 보상 사이 최소 간격 (광고 길이보다 빠른 스크립트 연타 차단)
    point_admin_adjust_max: int = 1_000_000  # 관리자 수동 조정 1회 한도 (절댓값)
    spotlight_cost: int = 100             # 상단 노출권 가격
    spotlight_hours: int = 24             # 상단 노출 지속 시간
    coupon_valid_days: int = 30           # 교환한 쿠폰 유효기간(일)

    # 신고 - 처리 완료된 신고가 이 수 이상 쌓이면 대상 계정을 자동 비활성화
    report_auto_deactivate_threshold: int = 3

    # 로깅
    log_level: str = "INFO"               # DEBUG|INFO|WARNING|ERROR
    log_format: str = "text"              # text|json (json 은 로그 수집기용 한 줄 JSON)
    log_file: str = ""                    # 지정하면 콘솔과 함께 파일에도 남긴다 (예: logs/app.log)
    log_file_max_bytes: int = 10 * 1024 * 1024  # 이 크기를 넘으면 파일을 교체(rotate)
    log_file_backup_count: int = 5        # 보관할 이전 로그 파일 수
    log_sql: bool = False                 # 실행되는 SQL 을 모두 로그로 남김 (개발용)

    # CORS - 프론트엔드 오리진. 쉼표로 구분. 운영에서는 .env 로 재정의할 것
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
