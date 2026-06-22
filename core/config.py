from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    measurements_topic: str = "measurements.test"
    measurements_dlq_topic: str = "measurements.test.dlq"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # AI summaries — provider selection + per-provider keys
    llm_provider: str = "gemini"  # gemini | claude | openai
    gemini_api_key: str = Field(default="", repr=False)
    anthropic_api_key: str = Field(default="", repr=False)
    openai_api_key: str = Field(default="", repr=False)

    # Auth / Rate limiting
    jwt_secret: str = Field(default="dev-jwt-secret-change-me", repr=False)
    redis_url: str = "redis://localhost:6379/0"

    # Alerts — Slack
    slack_webhook_url: str = Field(default="", repr=False)

    # Alerts — Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = Field(default="", repr=False)
    smtp_from_address: str = ""
    alert_email_recipients: str = ""  # comma-separated

    # Alerts — SMS (generic webhook, e.g. Twilio/Vonage)
    sms_webhook_url: str = ""
    sms_auth_token: str = Field(default="", repr=False)
    sms_from_number: str = ""
    sms_to_numbers: str = ""  # comma-separated

    # JIRA (optional)
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = Field(default="", repr=False)
    jira_project_key: str = "QUAL"

    # QMS integration
    qms_api_url: str = ""

    # Twilio SDK (optional — falls back to generic SMS webhook)
    twilio_account_sid: str = ""
    twilio_auth_token: str = Field(default="", repr=False)

    # ML Tool adapter selection (mlflow | gemini)
    ml_tool_name: str = "mlflow"

    # Dashboard URL for email alert links
    dashboard_url: str = "http://localhost:3000"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    api_auth_key: str = Field(repr=False)
    frontend_url: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allow_mock_data: bool = False

    # First-run bootstrap (seeded automatically on startup; see scripts/bootstrap.py)
    admin_username: str = "admin"
    admin_password: str = Field(default="", repr=False)
    seed_demo_data: bool = False

    # Autonomous monitoring loop (continuous SPC + alerting on the live stream)
    enable_autonomous_monitor: bool = True
    monitor_interval_seconds: int = 30

    # MES/QMS scheduled connector (auto-pulls measurements from the org's API).
    # These are configurable from the dashboard (see core/settings_store.py SPEC).
    enable_mes_connector: bool = True
    mes_poll_interval_seconds: int = 60
    mes_api_url: str = ""
    mes_api_token: str = Field(default="", repr=False)
    mes_auth_header: str = ""
    mes_auth_value: str = Field(default="", repr=False)
    mes_records_path: str = ""
    mes_field_map: str = ""
    mes_id_field: str = ""
    mes_since_param: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self

        # Reject mock data early when running in production mode.
        if self.allow_mock_data:
            raise ValueError("ALLOW_MOCK_DATA must be false in production")

        if len(self.api_auth_key) < 32:
            raise ValueError("API_AUTH_KEY must be rotated to a strong secret in production")

        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be rotated to a strong secret in production")

        if not self.frontend_url.strip():
            raise ValueError("FRONTEND_URL must be configured in production")

        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must not contain '*' in production")

        return self


# Singleton — import this everywhere
settings = Settings()
