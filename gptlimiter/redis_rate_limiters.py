# Standard library
import asyncio

# Third party
from redis import asyncio as aioredis

# Local
import token_counters as tc
from buckets import RedisBucket


############
# BASE CLASS
############


class RateLimiterWithRedis(object):
    def __init__(self, request_limit=200, token_limit=40000, redis_url="redis://localhost:5050"):
        # Rate limits
        self.request_limit = request_limit
        self.token_limit = token_limit

        # Redis
        self._redis_url = redis_url

        # Buckets
        self._request_bucket = None
        self._token_bucket = None
    
    async def _init_buckets(self):
        if self._request_bucket and self._token_bucket:
            return

        redis = await aioredis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)

        self._request_bucket = RedisBucket(
            self.request_limit,
            bucket_key="requests",
            redis=redis
        )
        self._token_bucket = RedisBucket(
            self.token_limit,
            bucket_key="tokens",
            redis=redis
        )
    
    async def _multi_acquire(self, num_tokens):
        await self._init_buckets()
        await asyncio.gather(
            self._request_bucket.acquire(1),
            self._token_bucket.acquire(num_tokens)
        )

        return


######
# MAIN
######


class ChatRateLimiterWithRedis(RateLimiterWithRedis):
    async def acquire(self, messages, max_tokens=15, n=1, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_chat_request(messages, max_tokens, n)
        await self._multi_acquire(num_tokens)

        return


class CompletionRateLimiterWithRedis(RateLimiterWithRedis):
    async def acquire(self, prompt, max_tokens=15, n=1, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_completion_request(prompt, max_tokens, n)
        await self._multi_acquire(num_tokens)

        return


class EmbeddingRateLimiterWithRedis(RateLimiterWithRedis):
    async def acquire(self, input, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_embedding_request(input)
        await self._multi_acquire(num_tokens)

        return