import asyncio
import json
from datetime import datetime, timedelta
from loguru import logger
from sqlmodel import select

from app.core.database import async_session_factory
from app.models.sync import SyncTask

from typing import Optional

class DocumentSyncService:
    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        logger.info("Starting DocumentSyncService background loop...")
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DocumentSyncService stopped.")

    async def _sync_loop(self):
        while self._running:
            try:
                await self._process_due_tasks()
            except Exception as e:
                logger.error(f"Error in Sync Loop: {e}")
            
            # Check every 60 seconds
            await asyncio.sleep(60)

    async def _process_due_tasks(self):
        now = datetime.utcnow()
        async with async_session_factory() as session:
            # Find tasks that are due
            query = select(SyncTask).where(SyncTask.status == "idle")
            # In a real app we would use SQL filtering for next_run_at < now, but for MVP we load all and filter
            results = await session.execute(query)
            tasks = results.scalars().all()
            
            for task in tasks:
                if not task.next_run_at or task.next_run_at <= now:
                    await self._execute_task(session, task)

    async def _execute_task(self, session, task: SyncTask):
        logger.info(f"Executing Sync Task {task.id} for KB {task.knowledge_base_id} (Source: {task.source_type})")
        task.status = "running"
        task.last_run_at = datetime.utcnow()
        await session.commit()

        try:
            # Simulate fetching external content based on source type
            await asyncio.sleep(3) # simulate network IO
            
            if task.source_type == "github":
                logger.info(f"Syncing from GitHub repo using config: {task.config_json}")
            elif task.source_type == "notion":
                logger.info(f"Syncing from Notion workspace using config: {task.config_json}")
            elif task.source_type == "confluence":
                logger.info(f"Syncing from Confluence using config: {task.config_json}")
            else:
                logger.warning(f"Unknown Sync Source: {task.source_type}")

            # E.g. trigger Ingestion Pipeline here for the fetched documents
            # from app.batch.controller import start_ingestion
            # start_ingestion(kb_id=task.knowledge_base_id, files=new_files)

            task.status = "idle"
            task.last_error = None
            
            # Schedule next run (e.g. naive 24 hours later if cron means daily, or parse cron)
            # For MVP, just schedule next run to +24 hours
            task.next_run_at = datetime.utcnow() + timedelta(days=1)
            
            logger.info(f"Sync Task {task.id} completed. Next run scheduled at {task.next_run_at}")
        
        except Exception as e:
            logger.error(f"Sync Task {task.id} failed: {e}")
            task.status = "idle"
            task.last_error = str(e)
            # Re-try shortly
            task.next_run_at = datetime.utcnow() + timedelta(minutes=5)
            
        finally:
            await session.commit()

sync_service = DocumentSyncService()
