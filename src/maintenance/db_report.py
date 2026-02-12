"""Simple DB reporter: lists problematic tasks and recent ERROR logs.

Run with: .venv/bin/python scripts/db_report.py
"""

import asyncio
import sys
import traceback
from datetime import datetime

from sqlalchemy import select

from src.brain.memory.db.manager import db_manager
from src.brain.memory.db.schema import LogEntry, Task, TaskStep


async def report(limit_tasks: int = 50, limit_logs: int = 200):
    try:
        await db_manager.initialize()
    except Exception:
        traceback.print_exc()
        return 1

    if not db_manager.available:
        return 2

    try:
        async with await db_manager.get_session() as s:
            # Tasks
            q = select(Task).where(Task.status.in_(["PENDING", "RUNNING", "FAILED"]))
            q = q.order_by(Task.created_at.desc()).limit(limit_tasks)
            tasks = await s.execute(q)
            tasks = tasks.scalars().all()
            if not tasks:
                pass
            for t in tasks:
                steps = await s.execute(
                    select(TaskStep)
                    .where(TaskStep.task_id == t.id)
                    .order_by(TaskStep.sequence_number),
                )
                for st in steps.scalars().all():
                    if st.status != "SUCCESS":
                        pass

            # Recent ERROR logs
            logs = await s.execute(
                select(LogEntry)
                .where(LogEntry.level.in_(["ERROR", "CRITICAL", "FATAL"]))
                .order_by(LogEntry.timestamp.desc())
                .limit(limit_logs),
            )
            logs = logs.scalars().all()
            if not logs:
                pass
            for l in logs:
                l.timestamp.isoformat() if isinstance(l.timestamp, datetime) else l.timestamp

    except Exception:
        traceback.print_exc()
        return 3

    return 0


def main():
    try:
        rc = asyncio.run(report())
        sys.exit(rc)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
