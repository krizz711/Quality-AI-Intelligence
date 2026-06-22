from __future__ import annotations

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings

logger = logging.getLogger(__name__)

# Try to use Redis-backed storage when available; fall back to in-memory storage
# so unit tests and local runs without Redis still work.
try:
	# Test Redis connection first to avoid runtime errors during request handling.
	from redis import Redis

	try:
		redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
		redis_client.ping()
		limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
	except Exception:
		# In production we must have Redis available; fail fast so deployments don't
		# start with degraded or unsafe rate limiting. For local/dev runs we fall
		# back to in-memory storage to make developer experience smooth.
		if settings.is_production:
			raise RuntimeError("Redis at %s unreachable but required in production" % settings.redis_url)
		logger.warning("Redis unreachable, using in-memory rate limiter for tests/local runs")
		limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
except Exception as exc:  # defensive fallback
	logger.warning("Rate limiter initialization failed, falling back to in-memory: %s", exc)
	limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

__all__ = ["limiter"]
