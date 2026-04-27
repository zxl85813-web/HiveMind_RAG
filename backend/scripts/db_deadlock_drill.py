import asyncio
import time
import argparse
import random
import sys
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import text
from sqlmodel import select, desc

# 🏗️ [Setup]: Path and Context
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.sdk.core.logging import setup_script_context, get_trace_logger
from app.core.database import async_session_factory
from app.models.chat import Conversation, Message

setup_script_context("db_deadlock_drill")
logger = get_trace_logger("scripts.db_deadlock_drill")

async def get_db_stats():
    """Query PostgreSQL system views for lock info."""
    async with async_session_factory() as session:
        # Check for active locks and waiting queries
        lock_query = text("""
            SELECT count(*) as lock_count 
            FROM pg_locks 
            WHERE granted = false;
        """)
        activity_query = text("""
            SELECT count(*) as active_conns 
            FROM pg_stat_activity 
            WHERE state = 'active';
        """)
        
        try:
            locks = (await session.execute(lock_query)).scalar()
            conns = (await session.execute(activity_query)).scalar()
            return {"waiting_locks": locks, "active_conns": conns}
        except Exception as e:
            return {"error": str(e)}

async def simulate_contention(user_id: int, conv_id: str, duration: int):
    """Simulate heavy updates/inserts on a single conversation (Contention)."""
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        async with async_session_factory() as session:
            try:
                # 1. Update Conversation Title (Write Lock)
                stmt = select(Conversation).where(Conversation.id == conv_id)
                res = await session.execute(stmt)
                conv = res.scalar_one_or_none()
                if conv:
                    conv.title = f"Stress Update {random.randint(1, 1000)}"
                    session.add(conv)
                    
                    # 2. Insert a Message (Table/Index Contention)
                    msg = Message(conversation_id=conv_id, role="system", content=f"Perf ping {count}")
                    session.add(msg)
                    
                    await session.commit()
                    count += 1
                await asyncio.sleep(random.uniform(0.01, 0.05))
            except Exception as e:
                logger.error(f"User {user_id} error: {e}")
                await session.rollback()
    return count

async def trigger_deadlock_probe():
    """
    Attempt to create a classic AB-BA deadlock.
    Note: Postgres detection might kill one transaction quickly.
    """
    logger.info("⚔️ Launching Deadlock Probe (Row-Level Conflict)...")
    
    # Ensure we have at least 2 conversations
    async with async_session_factory() as session:
        res = await session.execute(select(Conversation).limit(2))
        convs = res.scalars().all()
        if len(convs) < 2:
            logger.warning("Not enough conversations for deadlock probe.")
            return

    c1_id, c2_id = convs[0].id, convs[1].id

    async def task_a():
        async with async_session_factory() as session:
            # Lock C1
            await session.execute(text(f"SELECT * FROM conversations WHERE id = '{c1_id}' FOR UPDATE"))
            logger.debug("Task A: Locked C1")
            await asyncio.sleep(0.5)
            # Try to lock C2
            logger.debug("Task A: Requesting C2...")
            await session.execute(text(f"SELECT * FROM conversations WHERE id = '{c2_id}' FOR UPDATE"))
            await session.commit()

    async def task_b():
        async with async_session_factory() as session:
            # Lock C2
            await session.execute(text(f"SELECT * FROM conversations WHERE id = '{c2_id}' FOR UPDATE"))
            logger.debug("Task B: Locked C2")
            await asyncio.sleep(0.5)
            # Try to lock C1
            logger.debug("Task B: Requesting C1...")
            await session.execute(text(f"SELECT * FROM conversations WHERE id = '{c1_id}' FOR UPDATE"))
            await session.commit()

    try:
        await asyncio.gather(task_a(), task_b())
        logger.info("✅ Deadlock probe finished without incident (or resolved by DB).")
    except Exception as e:
        logger.warning(f"💥 Deadlock Detected/Resolved: {e}")

async def run_drill(concurrency: int, duration: int):
    # 1. Setup a Target Conversation
    async with async_session_factory() as session:
        # Find an existing user (admin)
        from app.models.chat import User
        res = await session.execute(select(User).where(User.username == "admin"))
        user = res.scalar_one_or_none()
        if not user:
            logger.error("User 'admin' not found. Please run seed script first.")
            return

        target = Conversation(user_id=user.id, title="Global Hot Row")
        session.add(target)
        await session.commit()
        await session.refresh(target)
        hot_conv_id = target.id

    logger.info(f"🚀 Starting DB Performance Drill | Concurrency: {concurrency} | Duration: {duration}s")
    
    start_time = time.perf_counter()
    
    # 2. Run Contention Tasks
    tasks = [simulate_contention(i, hot_conv_id, duration) for i in range(concurrency)]
    # Add Deadlock Probe in the middle
    tasks.append(trigger_deadlock_probe())
    
    results = await asyncio.gather(*tasks)
    
    total_ops = sum(r for r in results if isinstance(r, int))
    elapsed = time.perf_counter() - start_time
    
    stats = await get_db_stats()
    
    logger.success(f"""
🏁 DB Drill Results:
---------------------------------
Total Write Transactions: {total_ops}
Effective RPS: {total_ops / elapsed:.2f}
Peak Active Connections: {stats.get('active_conns')}
Waiting Locks: {stats.get('waiting_locks')}
Elapsed Time: {elapsed:.2f}s
---------------------------------
    """)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()
    
    asyncio.run(run_drill(args.concurrency, args.duration))
