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
    "electron .",
    "vite",
    "mcp-server-macos-use",
    "mcp-server-sequential-thinking",
    "mcp-server-filesystem",
    "uvicorn",
]

# Ports to check and free
TARGET_PORTS = [8000, 8080, 8090]  # Brain, Vibe, Proxy, etc.


def get_process_list():
    """Get list of running processes with PIDs and command lines."""
    try:
        # ps -eo pid,command
        result = subprocess.run(
            ["ps", "-eo", "pid,command"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        processes = []
        for line in lines[1:]:  # Skip header
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
        pass
    except ProcessLookupError:
        pass
    except PermissionError:
        print(f"[CLEANUP] Permission denied killing PID {pid}")
    except Exception as e:
        print(f"[CLEANUP] Error killing PID {pid}: {e}")


def main():
    print("[CLEANUP] Checking for lingering processes...")

    processes = get_process_list()
    killed_count = 0

    for pid, cmd in processes:
        # Check against signatures
        if any(sig in cmd for sig in TARGET_SIGNATURES):
            # Double check it's not us (though we are 'ensure_clean_start.py')
            if "ensure_clean_start.py" in cmd:
                continue

            kill_process(pid, cmd[:50] + "...")
            killed_count += 1

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
                            killed_count += 1
                        except ProcessLookupError:
                            pass
                        except Exception:
                            pass
        except Exception:
            pass

    if killed_count > 0:
        print(f"[CLEANUP] Terminated {killed_count} processes.")
        # Brief pause to let OS reclaim resources
        time.sleep(1)
    else:
        print("[CLEANUP] System clean.")


if __name__ == "__main__":
    main()
