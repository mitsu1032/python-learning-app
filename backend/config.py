"""
設定管理モジュール
環境変数から設定を読み込み、アプリケーション全体で使用
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    """
    アプリケーション設定クラス
    環境変数から自動的に値を読み込む
    """

    # API設定
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="使用するClaudeモデル"
    )

    # アプリケーション設定
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="アプリケーション環境"
    )
    debug: bool = Field(default=True, description="デバッグモード")
    database_path: str = Field(
        default="./data/learning.db",
        description="SQLiteデータベースパス"
    )

    # セキュリティ設定
    cors_origins: str = Field(
        default="http://localhost,http://localhost:80",
        description="CORS許可オリジン（カンマ区切り）"
    )
    rate_limit_requests: int = Field(
        default=60,
        description="レート制限（リクエスト数/ウィンドウ）"
    )
    rate_limit_window: int = Field(
        default=60,
        description="レート制限ウィンドウ（秒）"
    )

    # ログ設定
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="ログレベル"
    )

    # キャッシュ設定
    cache_ttl: int = Field(default=3600, description="キャッシュTTL（秒）")
    cache_max_size: int = Field(default=1000, description="キャッシュ最大サイズ")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS許可オリジンをリストで取得"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    設定のシングルトンインスタンスを取得
    キャッシュにより同じインスタンスを返す
    """
    return Settings()


# グローバル設定インスタンス（簡易アクセス用）
settings = get_settings()
