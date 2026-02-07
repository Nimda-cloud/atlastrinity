#!/usr/bin/env python3
"""
Atlas Trinity Pre-Flight Cleanup
Aggressively kills lingering processes from previous sessions to ensure a clean start.
"""

import os
import signal
import subprocess
import time

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
]

# Ports to check and free
TARGET_PORTS = [8000, 8080, 8085, 8090]  # Brain, Vibe, Proxy, etc.


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
    except Exception as e:
        print(f"[CLEANUP] Failed to list processes: {e}")
        return []


def kill_process(pid, name):
    """Try to kill a process gracefully, then forcefully."""
    try:
        # Skip self
        if pid == os.getpid():
            return

        print(f"[CLEANUP] Killing {name} (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        # Give it a moment (non-blocking in this script structure,
        # but practically we just fire SIGTERM first)
    except ProcessLookupError:
        pass
    except PermissionError:
        print(f"[CLEANUP] Permission denied killing PID {pid}")
    except Exception as e:
        print(f"[CLEANUP] Error killing PID {pid}: {e}")


def main():
    print("[CLEANUP] Checking for lingering processes...")

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
                        print(f"[CLEANUP] Freeing port {port} (PID: {pid})...")
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
        print(f"[CLEANUP] Terminated {killed_count} processes.")
        # Brief pause to let OS reclaim resources
        time.sleep(1)
    else:
        print("[CLEANUP] System clean.")


if __name__ == "__main__":
    main()
