
import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Mock constants
VIBE_BINARY = os.path.expanduser("~/.local/bin/vibe")
VIBE_WORKSPACE = os.path.expanduser("~/.config/atlastrinity/vibe_workspace")

async def run_vibe():
    argv = [
        "script", "-q", "/dev/null",
        VIBE_BINARY, 
        "-p", "Create a file called '/tmp/hello_vibe_test.py' with a simple hello world script that prints 'Hello from Vibe MCP!'.", 
        "--output", "streaming",
        "--auto-approve",
        "--max-turns", "5"
    ]
    
    cwd = VIBE_WORKSPACE
    os.makedirs(cwd, exist_ok=True)
    
    env = os.environ.copy()
    # Reproduce exactly what vibe_server.py does currently
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"
    
    print(f"Running: {argv}")
    print(f"CWD: {cwd}")
    print(f"Env TERM: {env.get('TERM')}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL
        )
        
        stdout_chunks = []
        stderr_chunks = []
        
        async def read_stream(stream, chunks, name):
            while True:
                data = await stream.read(512)
                if not data:
                    break
                text = data.decode(errors='replace')
                chunks.append(text)
                print(f"[{name}] {text}")
                
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, stdout_chunks, "STDOUT"),
                read_stream(process.stderr, stderr_chunks, "STDERR"),
                process.wait()
            ),
            timeout=10.0
        )
        
        print(f"Exit code: {process.returncode}")
        
    except asyncio.TimeoutError:
        print("TIMED OUT")
        if process:
            process.terminate()

if __name__ == "__main__":
    asyncio.run(run_vibe())
