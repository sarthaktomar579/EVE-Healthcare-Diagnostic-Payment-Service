import json
import time
from typing import Any, Optional
from app.core.config import settings
from app.core.logging import logger

try:
    import redis
except ImportError:
    redis = None

_memory_cache: dict[str, tuple[float, str]] = {}


class CacheManager:
    def __init__(self):
        self._redis_client: Optional[Any] = None
        self._redis_available: bool = False
        self._init_client()

    def _init_client(self):
        if not settings.CACHE_ENABLED or redis is None:
            if redis is None:
                logger.debug("Redis package not installed. Utilizing in-memory cache.")
            return

        try:
            client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            client.ping()
            self._redis_client = client
            self._redis_available = True
            logger.info("Connected to Redis cache successfully.")
        except Exception as e:
            self._redis_available = False
            self._redis_client = None
            logger.warning(
                f"Redis unavailable ({str(e)}). Falling back to in-memory TTL cache."
            )

    def get(self, key: str) -> Optional[Any]:
        if not settings.CACHE_ENABLED:
            return None

        if self._redis_available and self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                logger.debug(f"Redis get failed: {e}. Falling back to memory.")

        # In-memory fallback
        if key in _memory_cache:
            expires_at, val = _memory_cache[key]
            if time.time() < expires_at:
                return json.loads(val)
            else:
                del _memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        if not settings.CACHE_ENABLED:
            return False

        ttl = ttl_seconds or settings.CACHE_DEFAULT_TTL_SECONDS
        json_val = json.dumps(value, default=str)

        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(key, ttl, json_val)
                return True
            except Exception as e:
                logger.debug(f"Redis set failed: {e}. Falling back to memory.")

        # In-memory fallback
        _memory_cache[key] = (time.time() + ttl, json_val)
        return True

    def delete(self, key: str) -> bool:
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        _memory_cache.pop(key, None)
        return True

    def invalidate_prefix(self, prefix: str):
        """Invalidate all keys matching the prefix"""
        if self._redis_available and self._redis_client:
            try:
                keys = self._redis_client.keys(f"{prefix}*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception:
                pass
        # Clear in-memory
        to_del = [k for k in _memory_cache if k.startswith(prefix)]
        for k in to_del:
            _memory_cache.pop(k, None)


cache = CacheManager()
