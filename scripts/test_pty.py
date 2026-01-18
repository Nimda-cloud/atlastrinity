
import asyncio
import os
import pty
import sys
from typing import List

VIBE_BINARY = os.path.expanduser("~/.local/bin/vibe")
VIBE_WORKSPACE = os.path.expanduser("~/.config/atlastrinity/vibe_workspace")

async def run_vibe_pty():
    prompt = "Create a file called '/tmp/hello_vibe_test.py' with a simple hello world script that prints 'Hello from Vibe MCP!'."
    argv = [
        VIBE_BINARY, 
        "-p", prompt, 
        "--output", "streaming",
        "--auto-approve",
        "--max-turns", "5"
    ]
    
    cwd = VIBE_WORKSPACE
    os.makedirs(cwd, exist_ok=True)
    
    # Create PTY
    master, slave = pty.openpty()
    
    env = os.environ.copy()
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"
    
    print(f"Running via PTY: {argv}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=env,
            stdout=slave,
            stderr=slave, # Combine stderr to PTY
            stdin=slave,
            close_fds=True # Important
        )
        os.close(slave) # Check if this is safe? Yes, parent doesn't need slave.
        
        # Create StreamReader for master
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, os.fdopen(master, 'rb', buffering=0))
        
        chunks = []
        
        async def read_loop():
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                text = data.decode(errors='replace')
                chunks.append(text)
                print(f"[PTY] {text}", end="")
        
        await asyncio.wait_for(
            asyncio.gather(
                read_loop(),
                process.wait()
            ),
            timeout=10.0
        )
        
        print(f"\nExit code: {process.returncode}")
        
    except Exception as e:
        print(f"\nError: {e}")
        if 'process' in locals():
            try:
                process.terminate()
            except: pass

if __name__ == "__main__":
    asyncio.run(run_vibe_pty())
