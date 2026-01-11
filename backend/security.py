"""
セキュリティミドルウェアとユーティリティ
"""
import time
import re
import html
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import os


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    レート制限ミドルウェア
    IPアドレスベースでリクエスト数を制限
    """

    def __init__(self, app, requests_per_window: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # ヘルスチェックはレート制限から除外
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # 古いリクエストを削除
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < self.window_seconds
        ]

        # レート制限チェック
        if len(self.request_counts[client_ip]) >= self.requests_per_window:
            raise HTTPException(
                status_code=429,
                detail="リクエスト数が制限を超えました。しばらく待ってから再試行してください。"
            )

        # リクエストを記録
        self.request_counts[client_ip].append(current_time)

        response = await call_next(request)

        # レート制限ヘッダーを追加
        remaining = self.requests_per_window - len(self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPアドレスを取得（プロキシ対応）"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    セキュリティヘッダーを追加するミドルウェア
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # セキュリティヘッダーを追加
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # 本番環境ではHSTSを有効化
        if os.getenv("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class InputSanitizer:
    """
    入力サニタイズユーティリティ
    """

    # 危険なPythonコードパターン
    DANGEROUS_PATTERNS = [
        r"import\s+os",
        r"import\s+subprocess",
        r"import\s+sys",
        r"from\s+os\s+import",
        r"from\s+subprocess\s+import",
        r"__import__",
        r"exec\s*\(",
        r"eval\s*\(",
        r"open\s*\([^)]*['\"][wax]",  # ファイル書き込み
        r"os\.system",
        r"os\.popen",
        r"subprocess\.",
        r"shutil\.",
        r"pickle\.",
        r"__builtins__",
        r"globals\s*\(",
        r"locals\s*\(",
        r"compile\s*\(",
    ]

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """HTMLエスケープ"""
        return html.escape(text)

    @classmethod
    def validate_python_code(cls, code: str) -> tuple[bool, str | None]:
        """
        Pythonコードの安全性を検証

        Returns:
            tuple: (is_safe, error_message)
        """
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"危険なコードパターンが検出されました: {pattern}"
        return True, None

    @classmethod
    def sanitize_keyword(cls, keyword: str, max_length: int = 100) -> str:
        """
        検索キーワードのサニタイズ
        """
        # 長さ制限
        keyword = keyword[:max_length]
        # HTMLエスケープ
        keyword = html.escape(keyword)
        # 空白の正規化
        keyword = " ".join(keyword.split())
        return keyword


def get_cors_origins() -> list[str]:
    """
    環境変数からCORS許可オリジンを取得
    """
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:80")
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def setup_security(app):
    """
    アプリケーションにセキュリティミドルウェアを設定
    """
    # レート制限の設定を環境変数から取得
    rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # ミドルウェアを追加（逆順で適用される）
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=rate_limit_requests,
        window_seconds=rate_limit_window
    )
