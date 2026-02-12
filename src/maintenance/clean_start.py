import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Signatures of processes to kill
# We match against the full command line
TARGET_SIGNATURES = [
    "brain.server",
    "scripts/watch_config.py",
    "mcp_server/vibe_server.py",
    "universal_proxy.py",
    "electron .",
    "vite",
    "mcp-server-macos-use",
    "mcp-server-sequential-thinking",
    "mcp-server-filesystem",
    "uvicorn",
    "redis-server",
    "redis-cli",
]

# Ports to check and free
TARGET_PORTS = [8000, 8080, 8085, 8086, 8090, 6379]  # Brain, Vibe, Proxies, Redis, etc.


def get_process_list() -> list[tuple[int, str]]:
    """Get list of running processes with PIDs and command lines."""
    try:
        # ps -eo pid,command
        result = subprocess.run(
            ["ps", "-eo", "pid,command"], capture_output=True, text=True, check=True
        )
        stdout: str = result.stdout
        lines: list[str] = stdout.strip().split("\n")
        processes: list[tuple[int, str]] = []
        for i in range(1, len(lines)):  # Skip header
            line: str = lines[i]
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                processes.append((int(parts[0]), parts[1]))
        return processes
    except Exception:
        return []


def kill_process(pid, name):
    """Try to kill a process gracefully, then forcefully."""
    try:
        # Skip self
        if pid == os.getpid():
            return

        os.kill(pid, signal.SIGTERM)

        # Give it a moment (non-blocking in this script structure,
        # but practically we just fire SIGTERM first)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass
    except Exception:
        pass


def main():

    processes: list[tuple[int, str]] = get_process_list()
    terminated_pids: list[int] = []

    for item in processes:
        pid: int = item[0]
        cmd: str = item[1]
        # Check against signatures
        if any(sig in cmd for sig in TARGET_SIGNATURES):
            # Double check it's not us (though we are 'ensure_clean_start.py')
            if "ensure_clean_start.py" in cmd:
                continue

            kill_process(pid, cmd)
            terminated_pids.append(pid)

    # Port cleanup (lsof)
    for port in TARGET_PORTS:
        try:
            # lsof -t -i:PORT
            res = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True)
            pids = res.stdout.strip().split()
            for p in pids:
                if p:
                    pid = int(p)
                    if pid != os.getpid():
                        try:
                            os.kill(pid, signal.SIGKILL)  # Ports need force usually
                            terminated_pids.append(pid)
                        except ProcessLookupError:
                            pass
                        except Exception:
                            pass
        except Exception:
            pass

    killed_count: int = len(terminated_pids)
    if killed_count > 0:
        # Brief pause to let OS reclaim resources
        time.sleep(1)
    else:
        pass


if __name__ == "__main__":
    main()
