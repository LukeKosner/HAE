from upstash_redis.asyncio import Redis
import os
import asyncio


async def user_history(user_id: str, return_chats: bool) -> dict:

    redis = Redis(
        url=os.getenv("UPSTASH_REDIS_HISTORY_REST_URL"),
        token=os.getenv("UPSTASH_REDIS_HISTORY_REST_TOKEN"),
    )

    cursor = 0
    results = []

    # Use async scan to fetch keys
    while True:
        cursor, keys = await redis.scan(cursor, match=f"{user_id}*")
        results.extend(keys)
        if cursor == 0:
            break

    if return_chats:

        # Use asyncio.gather to fetch all chat histories concurrently
        chat_histories = await asyncio.gather(
            *[redis.lrange(key, 0, -1) for key in results]
        )

        return {key: chat for key, chat in zip(results, chat_histories)}

    return results


async def chat_history(user_id: str, conversation_id: str) -> list:
    redis = Redis(
        url=os.getenv("UPSTASH_REDIS_HISTORY_REST_URL"),
        token=os.getenv("UPSTASH_REDIS_HISTORY_REST_TOKEN"),
    )

    data = await redis.lrange(f"{user_id}/{conversation_id}", 0, -1)

    return data
