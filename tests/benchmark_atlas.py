import asyncio
import time

from src.brain.agents.atlas import Atlas


async def benchmark_chat():
    atlas = Atlas()

    # First call - should be fast (Fast-Path Greeting)
    print("\nTest 1: Simple Greeting (Fast-Path)...")
    start = time.time()
    response = await atlas.chat("Привіт!")
    end = time.time()
    print(f"Response: {response}")
    print(f"Time: {end - start:.2f}s")

    # Second call - Info query (Should trigger cache refresh on first run)
    print("\nTest 2: Info Query (Tool Discovery)...")
    start = time.time()
    response = await atlas.chat("Яка сьогодні погода в Києві?")
    end = time.time()
    print(f"Response: {response}")
    print(f"Time: {end - start:.2f}s")

    # Third call - Info query (Should use CACHE)
    print("\nTest 3: Info Query (Cached Tools)...")
    start = time.time()
    response = await atlas.chat("Хто такий Олег Миколайович?")
    end = time.time()
    print(f"Response: {response}")
    print(f"Time: {end - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(benchmark_chat())
