
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.brain.db.manager import db_manager
from src.brain.mcp_manager import mcp_manager
from src.brain.db.schema import RecoveryAttempt, TaskStep, Session, Task
from sqlalchemy import select

async def verify_recovery_flow():
    print("🚀 Starting Recovery Flow Verification...")
    
    # 1. Initialize DB
    await db_manager.initialize()
    if not db_manager.available:
        print("❌ Database not available")
        return

    async with await db_manager.get_session() as session:
        # Generate unique IDs for this test run
        test_sess_id = uuid.uuid4()
        test_task_id = uuid.uuid4()
        
        # 2. Created dummy data
        db_sess = Session(id=test_sess_id, started_at=datetime.utcnow())
        db_task = Task(id=test_task_id, session_id=test_sess_id, goal="Test Vibe Recovery")
        session.add(db_sess)
        session.add(db_task)
        await session.commit()

        # Create a step
        step = TaskStep(
            task_id=test_task_id,
            sequence_number=1,  # Use a standard sequence number
            action="Test Action",
            tool="filesystem",
            status="FAILED"
        )
        session.add(step)
        await session.commit()
        
        step_id_db = step.id
        print(f"✅ Created dummy step in DB (ID: {step_id_db}, Seq: 1)")

        # 3. Inject a past recovery attempt
        past_rec = RecoveryAttempt(
            step_id=step_id_db,
            vibe_text="First attempt failed because of missing permission",
            success=False,
            duration_ms=5000,
            depth=1,
            recovery_method="vibe",
            error_before="Permission Denied"
        )
        session.add(past_rec)
        await session.commit()
        print("✅ Injected past recovery attempt record")

    # 4. Mock recovery fetch
    print("⚡ Triggering simulated recovery logic...")
    
    technical_trace = ""
    recovery_history = ""
    
    try:
        # Use the same IDs as created above
        seq_num = 1
        task_id_db = test_task_id
        
        # 1. Technical Trace (Actions)
        sql_trace = "SELECT tool_name, arguments, result FROM tool_executions WHERE step_id IN (SELECT id FROM task_steps WHERE sequence_number = :seq AND task_id = :task_id) ORDER BY created_at DESC LIMIT 3;"
        db_rows = await mcp_manager.query_db(sql_trace, {"seq": seq_num, "task_id": str(task_id_db)})
        if db_rows:
            technical_trace = "\nTECHNICAL EXECUTION TRACE:\n" + json.dumps(db_rows, indent=2, default=str)
        
        # 2. Recovery History (Attempts)
        sql_rec = "SELECT success, duration_ms, vibe_text FROM recovery_attempts WHERE step_id IN (SELECT id FROM task_steps WHERE sequence_number = :seq AND task_id = :task_id) ORDER BY created_at DESC LIMIT 2;"
        rec_rows = await mcp_manager.query_db(sql_rec, {"seq": seq_num, "task_id": str(task_id_db)})
        
        if rec_rows:
            recovery_history = "\nPAST RECOVERY ATTEMPTS:\n"
            for r in rec_rows:
                # RAW DB ROW contains column names as keys
                success_val = r.get("success")
                duration_val = r.get("duration_ms")
                vibe_text_val = r.get("vibe_text")
                
                status = "Success" if success_val else "Failed"
                recovery_history += f"- Status: {status}, Duration: {duration_val}ms\n"
                if not success_val and vibe_text_val:
                     recovery_history += f"  Report: {vibe_text_val[:500]}...\n"
    except Exception as e:
        print(f"❌ DB Query failed: {e}")

    print("\n🔍 Verification Analysis:")
    if "PAST RECOVERY ATTEMPTS" in recovery_history:
        print("✅ Recovery history successfully fetched from DB")
        print(f"   Content Preview:\n{recovery_history}")
    else:
        print("❌ Recovery history NOT found. Check SQL logic or task_id filtering.")

    if "First attempt failed" in recovery_history:
        print("✅ Correct failure report found in history")
    else:
        print("❌ Specific failure report missing from history")

    print("\n🏁 Integration test complete.")

if __name__ == "__main__":
    asyncio.run(verify_recovery_flow())
