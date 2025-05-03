import random
import asyncio

import aiohttp


def generate_dataset(size):
    return {
        'x': [random.random() for _ in range(size)],
        'y': [random.random() for _ in range(size)],
    }


async def get_size():
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.get("http://localhost:8080/size?feed=xy") as resp:
            data = await resp.json()
            return data['size']


async def clear():
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.put("http://localhost:8080/size?feed=xy", 
                              json={'size': 0}):
            pass


async def push_dataset(dataset):
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with client.post("http://localhost:8080/data?feed=xy", 
                               json=dataset):
            pass


async def main():
    await clear()
    dataset = generate_dataset(50_000)
    await push_dataset(dataset)
    print(await get_size())


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
