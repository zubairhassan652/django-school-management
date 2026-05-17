# school_management/utils/redis_client.py

import redis
from django.conf import settings
from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for caching and sessions"""

    def __init__(self):
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        try:
            redis_config = getattr(settings, 'REDIS_CONFIG', {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
            })

            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                decode_responses=True
            )

            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")

        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None

    def get(self, key):
        """Get value from Redis"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def set(self, key, value, expiry=3600):
        """Set value in Redis with expiry (default 1 hour)"""
        try:
            if self.redis_client:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                self.redis_client.setex(key, expiry, value)
                return True
            return False
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def delete(self, key):
        """Delete key from Redis"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
                return True
            return False
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def exists(self, key):
        """Check if key exists"""
        try:
            if self.redis_client:
                return self.redis_client.exists(key)
            return False
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    def cache_queryset(self, key, queryset, expiry=300):
        """Cache Django queryset"""
        try:
            data = list(queryset.values())
            return self.set(key, data, expiry)
        except Exception as e:
            logger.error(f"Cache queryset error: {e}")
            return False

    def get_or_set(self, key, callback, expiry=3600):
        """Get from cache or compute and cache"""
        cached = self.get(key)
        if cached is not None:
            return cached

        value = callback()
        self.set(key, value, expiry)
        return value


# Singleton instance
redis_client = RedisClient()