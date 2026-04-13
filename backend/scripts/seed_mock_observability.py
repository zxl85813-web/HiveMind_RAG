
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import async_session_factory
from app.models.observability import BaselineMetric, LLMMetric

async def seed_baseline_metrics(session: AsyncSession):
    print("Seeding baseline metrics...")
    metrics = ["TTFT (Baseline)", "LCP (Baseline)", "Total Latency (Baseline)", "API Fetch (Baseline)"]
    groups = ["control", "experiment"]
    
    # Base values for each metric (mean, stddev)
    base_values = {
        "TTFT (Baseline)": (950, 150),
        "LCP (Baseline)": (1200, 200),
        "Total Latency (Baseline)": (2500, 500),
        "API Fetch (Baseline)": (450, 100)
    }
    
    # Multiplier for experiment group (simulating 15-20% improvement)
    exp_multiplier = 0.82

    for metric_name in metrics:
        mean, std = base_values[metric_name]
        for group in groups:
            # Seed 30-50 samples per group
            count = random.randint(30, 50)
            current_mean = mean * (exp_multiplier if group == "experiment" else 1.0)
            
            for _ in range(count):
                val = random.gauss(current_mean, std)
                # Ensure value is positive
                val = max(val, 10.0)
                
                metric = BaselineMetric(
                    id=str(uuid.uuid4()),
                    metric_name=metric_name,
                    value=val,
                    session_id=str(uuid.uuid4()),
                    context={"grp": group, "ua": "Mock-Browser", "path": "/chat"},
                    created_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 10000))
                )
                session.add(metric)
    
    await session.commit()
    print("Baseline metrics seeded.")

async def seed_llm_metrics(session: AsyncSession):
    print("Seeding LLM performance metrics...")
    models = [
        ("DeepSeek-V3", "siliconflow", 150, 300),
        ("GLM-5 Pro", "siliconflow", 450, 600),
        ("DeepSeek-R1", "ark", 2200, 1200),
        ("GPT-4o-Mini", "openai", 180, 250)
    ]

    for name, provider, mean_lat, std_lat in models:
        # Seed 100 calls per model
        for _ in range(100):
            is_error = random.random() < 0.05 # 5% error rate
            latency = random.gauss(mean_lat, std_lat)
            latency = max(latency, 50.0)
            
            t_in = random.randint(100, 2000)
            t_out = random.randint(50, 1000)
            
            cost = (t_in * 0.0001 + t_out * 0.0002) / 1000 # dummy cost
            
            metric = LLMMetric(
                id=str(uuid.uuid4()),
                model_name=name,
                provider=provider,
                latency_ms=latency,
                tokens_input=t_in,
                tokens_output=t_out,
                cost=cost,
                is_error=is_error,
                error_type="TIMEOUT" if is_error else None,
                context={"task": "rag_query"},
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))
            )
            session.add(metric)
    
    await session.commit()
    print("LLM metrics seeded.")

async def main():
    async with async_session_factory() as session:
        await seed_baseline_metrics(session)
        await seed_llm_metrics(session)

if __name__ == "__main__":
    asyncio.run(main())
