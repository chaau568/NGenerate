# import redis
# from django.conf import settings

# redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


# def acquire_lock(key, timeout=3600):
#     return redis_client.set(key, "1", nx=True, ex=timeout)


# def release_lock(key):
#     redis_client.delete(key)


import redis
from django.conf import settings


redis_client = redis.Redis.from_url(
    settings.CELERY_BROKER_URL,
    decode_responses=True,
)


def acquire_lock(key, timeout=3600):
    return redis_client.set(key, "1", nx=True, ex=timeout)


def release_lock(key):
    redis_client.delete(key)
