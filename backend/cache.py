"""
キャッシュユーティリティ
シンプルなインメモリキャッシュとデコレータを提供
"""
import time
import hashlib
import json
from functools import wraps
from typing import Any, Callable, TypeVar, ParamSpec
from collections import OrderedDict
import threading

P = ParamSpec("P")
T = TypeVar("T")


class LRUCache:
    """
    LRU（Least Recently Used）キャッシュ実装
    スレッドセーフ、TTLサポート
    """

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Args:
            max_size: キャッシュの最大エントリ数
            ttl: キャッシュの有効期限（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """
        キャッシュから値を取得

        Args:
            key: キャッシュキー

        Returns:
            キャッシュされた値、または None（キーがない/期限切れの場合）
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # TTLチェック
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None

            # LRU: アクセスされたアイテムを末尾に移動
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """
        キャッシュに値を設定

        Args:
            key: キャッシュキー
            value: キャッシュする値
        """
        with self._lock:
            # 既存のキーがあれば削除
            if key in self._cache:
                del self._cache[key]

            # サイズ制限チェック
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (value, time.time())

    def delete(self, key: str) -> bool:
        """
        キャッシュからエントリを削除

        Args:
            key: キャッシュキー

        Returns:
            削除成功したかどうか
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """キャッシュを全クリア"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """現在のキャッシュサイズを取得"""
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """
        期限切れエントリを削除

        Returns:
            削除されたエントリ数
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# グローバルキャッシュインスタンス
_cache_instance: LRUCache | None = None


def get_cache() -> LRUCache:
    """グローバルキャッシュインスタンスを取得"""
    global _cache_instance
    if _cache_instance is None:
        from config import settings
        _cache_instance = LRUCache(
            max_size=settings.cache_max_size,
            ttl=settings.cache_ttl
        )
    return _cache_instance


def make_cache_key(*args, **kwargs) -> str:
    """
    引数からキャッシュキーを生成

    Args:
        *args: 位置引数
        **kwargs: キーワード引数

    Returns:
        ハッシュ化されたキャッシュキー
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int | None = None, key_prefix: str = ""):
    """
    関数の結果をキャッシュするデコレータ

    Args:
        ttl: このキャッシュ専用のTTL（Noneの場合はグローバル設定を使用）
        key_prefix: キャッシュキーのプレフィックス

    Usage:
        @cached(ttl=300, key_prefix="search")
        async def search_keywords(query: str):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache()
            cache_key = f"{key_prefix}:{func.__name__}:{make_cache_key(*args, **kwargs)}"

            # キャッシュヒットチェック
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 関数を実行
            result = await func(*args, **kwargs)

            # 結果をキャッシュ
            cache.set(cache_key, result)
            return result

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache()
            cache_key = f"{key_prefix}:{func.__name__}:{make_cache_key(*args, **kwargs)}"

            # キャッシュヒットチェック
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 関数を実行
            result = func(*args, **kwargs)

            # 結果をキャッシュ
            cache.set(cache_key, result)
            return result

        # async関数かどうかで適切なラッパーを返す
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(key_prefix: str = "") -> None:
    """
    指定されたプレフィックスを持つキャッシュを無効化
    現在の実装ではキャッシュ全体をクリア

    Args:
        key_prefix: 無効化するキャッシュのプレフィックス
    """
    cache = get_cache()
    cache.clear()
