import asyncio
import os
import pty
import subprocess

VIBE_BINARY = os.path.expanduser("~/.local/bin/vibe")
VIBE_WORKSPACE = os.path.expanduser("~/.config/atlastrinity/vibe_workspace")

async def run_vibe():
    argv = [
        "script",
        "-q",
        "/dev/null",
        VIBE_BINARY,
        "-p",
        "Create a file called '/tmp/hello_vibe_test.py' with a simple hello world script that prints 'Hello from Vibe MCP!'.",
        "--output",
        "streaming",
        "--auto-approve",
        "--max-turns",
        "5",
    ]

    cwd = VIBE_WORKSPACE
    os.makedirs(cwd, exist_ok=True)

    env = os.environ.copy()
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"

    print(f"Running: {argv}")
    print(f"CWD: {cwd}")
    print(f"Env TERM: {env.get('TERM')}")

    process = None
    master, slave = None, None
    loop = asyncio.get_event_loop()

    try:
        # PTY mode
        master, slave = pty.openpty()
        assert master is not None and slave is not None

        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=slave,
            stderr=slave,
            stdin=slave,
            text=True,
            preexec_fn=os.setsid,
        )
        os.close(slave)

        loop = asyncio.get_event_loop()
        stdout_chunks = []

        async def read_pty_stream():
            if master is None:
                return
            try:
                while True:
                    data = await loop.run_in_executor(None, os.read, int(master), 512)
                    if not data:
                        break
                    text = data.decode(errors="replace")
                    stdout_chunks.append(text)
                    print(f"[PTY] {text}", end="")
            except Exception as e:
                print(f"Read error: {e}")

        await asyncio.wait_for(
            asyncio.gather(read_pty_stream(), loop.run_in_executor(None, process.wait)),
            timeout=10.0,
        )

        print(f"Exit code: {process.returncode}")

    except TimeoutError:
        print("TIMED OUT")
        if process:
            process.terminate()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if master is not None:
            try:
                os.close(int(master))
            except:
                pass

if __name__ == "__main__":
    asyncio.run(run_vibe())
