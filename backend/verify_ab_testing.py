import asyncio
import uuid
import json
import traceback
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.observability import BaselineMetric
from app.services.observability_service import get_baseline_summary
from app.core.database import async_session_factory

async def verify_ab_testing():
    try:
        async with async_session_factory() as session:
            # 1. Clean up or just add new records
            session_id = str(uuid.uuid4())
            print(f"Testing with session_id: {session_id}")
            
            # Add control group data
            m1 = BaselineMetric(
                metric_name="TTFT (Baseline)",
                value=500.0,
                session_id=session_id,
                context={"grp": "control"}
            )
            m2 = BaselineMetric(
                metric_name="TTFT (Baseline)",
                value=600.0,
                session_id=session_id,
                context={"grp": "control"}
            )
            
            # Add experiment group data
            m3 = BaselineMetric(
                metric_name="TTFT (Baseline)",
                value=300.0,
                session_id=session_id,
                context={"grp": "experiment"}
            )
            m4 = BaselineMetric(
                metric_name="TTFT (Baseline)",
                value=400.0,
                session_id=session_id,
                context={"grp": "experiment"}
            )
            
            session.add_all([m1, m2, m3, m4])
            await session.commit()
            
            print("Data injected.")
            
            # 2. Call the summary function
            report = await get_baseline_summary(session)
            
            print("\nVerification Report:")
            print(json.dumps(report, indent=2))
            
            # 3. Assertions (simple prints)
            ttft = report.get("TTFT (Baseline)", {})
            control_stats = ttft.get("control", {})
            experiment_stats = ttft.get("experiment", {})
            
            print(f"\nControl Mean: {control_stats.get('mean')} (Expected ~550.0ish)")
            print(f"Experiment Mean: {experiment_stats.get('mean')} (Expected ~350.0ish)")
            
            if "control" in ttft and "experiment" in ttft:
                print("\n✅ BACKEND A/B TESTING VERIFICATION PASSED!")
            else:
                print("\n❌ VERIFICATION FAILED: Groups missing in summary.")
    except Exception as e:
        print("\n❌ ERROR DURING VERIFICATION:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_ab_testing())
