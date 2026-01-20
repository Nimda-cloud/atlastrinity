import asyncio
import json
import os
import sys

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(current_dir, "..")
src_path = os.path.join(root, "src")
sys.path.insert(0, root)
sys.path.insert(0, src_path)

from src.mcp_server.redis_server import redis_get, redis_set, redis_keys, redis_ttl, redis_hset, redis_hgetall, redis_info

async def verify_redis_mcp():
    print("--- Verifying Redis MCP Tools ---")
    
    # 1. Test basic set/get
    print("Testing redis_set/get...")
    await redis_set("test:trinity", "system_alive", ex_seconds=60)
    res = await redis_get("test:trinity")
    print(f"Get result: {res}")
    assert res["success"] is True
    assert res["value"] == "system_alive"

    # 2. Test TTL
    print("Testing redis_ttl...")
    ttl_res = await redis_ttl("test:trinity")
    print(f"TTL result: {ttl_res}")
    assert ttl_res["success"] is True
    assert ttl_res["ttl"] > 0

    # 3. Test Hash operations
    print("Testing redis_hset/hgetall...")
    await redis_hset("test:hash", {"agent": "atlas", "status": "active"})
    h_res = await redis_hgetall("test:hash")
    print(f"Hash result: {h_res}")
    assert h_res["success"] is True
    assert h_res["hash"]["agent"] == "atlas"

    # 4. Test Keys
    print("Testing redis_keys...")
    keys_res = await redis_keys("test:*")
    print(f"Keys result: {keys_res}")
    assert "test:trinity" in keys_res["keys"]

    # 5. Test Info
    print("Testing redis_info...")
    info_res = await redis_info()
    print(f"Info result: {info_res}")
    assert info_res["success"] is True

    print("\n[SUCCESS] All Redis MCP tools verified!")

if __name__ == "__main__":
    asyncio.run(verify_redis_mcp())
