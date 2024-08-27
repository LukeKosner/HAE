from upstash_redis.asyncio import Redis
import os
import json

from dotenv import load_dotenv


async def set_public(conversation_id: str, user_id: str) -> None:
    load_dotenv()
    redis = Redis(
        url=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_URL"),
        token=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_TOKEN"),
    )

    key = conversation_id
    key_type = await redis.type(key)

    if key_type == "list":
        existing_list = await redis.lrange(key, 0, -1)
        existing_data = {"messages": existing_list}
    elif key_type == "string":
        existing = await redis.get(key)
        existing_data = json.loads(existing) if existing else {}
    elif key_type == "none":
        existing_data = {}
    else:
        raise TypeError(f"Key {key} holds the wrong kind of value: {key_type}")

    # Update only the "public" field and add "user_id", while keeping the rest of the existing data
    existing_data.update({"public": True, "user_id": user_id})

    # Set the updated value back in Redis
    await redis.set(key, json.dumps(existing_data))
    return None


async def set_private(conversation_id: str, user_id: str) -> None:
    load_dotenv()
    redis = Redis(
        url=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_URL"),
        token=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_TOKEN"),
    )

    key = conversation_id
    existing = await redis.get(key)

    if existing:
        existing_data = json.loads(existing)
    else:
        existing_data = {}

    # Update only the "public" field, while keeping the rest of the existing data
    existing_data.update({"public": False})

    # Set the updated value back in Redis
    await redis.set(key, json.dumps(existing_data))
    return None


async def get_public(conversation_id: str) -> dict:
    history_redis = Redis(
        url=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_URL"),
        token=os.getenv("UPSTASH_REDIS_CONVERSATIONS_REST_TOKEN"),
    )

    # Get the value from Redis
    data = await history_redis.get(f"{conversation_id}")

    # Check if the data exists and parse it, otherwise return False
    if data is None:
        return False

    # Parse the JSON and get the "public" key, defaulting to False if it doesn't exist
    return {
        "public": json.loads(data).get("public", False),
        "user_id": json.loads(data).get("user_id"),
    }
