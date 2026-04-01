import asyncio
from typing import TypeVar
import httpx
from flask import flash, redirect, render_template, session
from functools import wraps
import os
import sqlalchemy
from models import *
import msgspec
import pythonping
from preferences import get_preference
from datetime import timedelta
timeout = httpx.Timeout(30.0, connect=5.0)
engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))


def snipe_it_get(
    endpoint: str,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    params=None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }

    response = httpx.get(
        snipe_url + endpoint, headers=headers, params=params, timeout=timeout
    )
    with open("debug_response.json", "w") as f:
        f.write(response.text)
    return response


T = TypeVar("T")


async def fetch_all(
    type: type[T],
    endpoint: str,
    batch_size: int = 10,
    threads: int = 10,
    params: dict = None,
) -> list[T]:
    semaphore = asyncio.Semaphore(threads)  # limit to 'threads' concurrent requests
    async with httpx.AsyncClient() as client:  # reuse the same client for all requests
        # get the total
        preflight = await snipe_it_get_async(
            endpoint,
            client=client,
            semaphore=semaphore,
            params={**(params or {}), "limit": 1, "offset": 0},
        )
        total = msgspec.json.decode(preflight.text, type=Paginated[T]).total
        tasks = [
            fetch_batch(
                type, endpoint, batch_size, batch_size * i, client, semaphore, params
            )
            for i in range((total // batch_size) + 1)
        ]
        result = await asyncio.gather(*tasks)  # wait for all tasks to complete
        return [
            item for batch in result for item in batch
        ]  # flatten the list syntactic sugar: https://stackoverflow.com/questions/20639180/explanation-of-how-nested-list-comprehension-works


async def fetch_batch(
    type: type[T],
    endpoint: str,
    batch_size: int,
    offset: int,
    client: httpx.AsyncClient = None,
    semaphore: asyncio.Semaphore = None,
    params: dict = None,
) -> list[T]:
    response = await snipe_it_get_async(
        endpoint,
        params={"limit": batch_size, "offset": offset, **(params or {})},
        client=client,
        semaphore=semaphore,
    )
    data = msgspec.json.decode(response.text, type=Paginated[type])
    return data.rows


async def snipe_it_get_async(
    endpoint,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    client=None,
    params=None,
    semaphore: asyncio.Semaphore = None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    client = client if client is not None else httpx.AsyncClient()
    if semaphore is not None:
        async with semaphore:
            return await client.get(
                snipe_url + endpoint, headers=headers, params=params, timeout=timeout
            )
    else:
        return await client.get(
            snipe_url + endpoint, headers=headers, params=params, timeout=timeout
        )


def snipe_it_post(
    endpoint,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    data=None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    response = httpx.post(
        snipe_url + endpoint, headers=headers, json=data, timeout=timeout
    )
    return response


def snipe_it_put(
    endpoint,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    data=None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    response = httpx.put(
        snipe_url + endpoint, headers=headers, json=data, timeout=timeout
    )
    return response


async def snipe_it_put_async(
    endpoint,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    client=None,
    data=None,
    semaphore: asyncio.Semaphore = None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    client = client if client is not None else httpx.AsyncClient()
    if semaphore is not None:
        async with semaphore:
            req = await client.put(
                snipe_url + endpoint, headers=headers, data=data, timeout=timeout
            )
            return req
            
    else:
        return await client.put(
            snipe_url + endpoint, headers=headers, data=data, timeout=timeout
        )


async def snipe_it_post_async(
    endpoint,
    api_key=get_preference("snipe-api-key"),
    snipe_url=get_preference("snipe-url"),
    client=None,
    data=None,
    semaphore: asyncio.Semaphore = None,
):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    client = client if client is not None else httpx.AsyncClient()
    if semaphore is not None:
        async with semaphore:
            return await client.post(
                snipe_url + endpoint, headers=headers, json=data, timeout=timeout
            )
    return await client.post(
        snipe_url + endpoint, headers=headers, json=data, timeout=timeout
    )


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def ping():
    output = pythonping.ping(get_preference("snipe-url").split("/")[2].split(":")[0], count=5, timeout=2)
    with sqlalchemy.orm.Session(engine) as session:
        kv_entry = session.get(KVStoreDb, "ping_rtt_ms")
        if kv_entry is None:
            kv_entry = KVStoreDb(key="ping_rtt_ms", value=str(output.rtt_avg_ms if output.success(2) else -1))
            session.add(kv_entry)
        else:
            kv_entry.value = str(output.rtt_avg_ms if output.success(2) else -1)
        session.commit()
    return output.rtt_avg_ms if output.success(2) else None
