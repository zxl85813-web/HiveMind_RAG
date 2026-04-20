
# @covers REQ-027
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from app.api.deps import get_current_admin
from app.common.response import ApiResponse
from app.models.chat import User
from app.services.governance.red_team_campaign import RedTeamCampaign
from pathlib import Path
import json
import os

router = APIRouter()

class RedTeamTrigger(BaseModel):
    scenarios: List[str] | None = None  # Specific scenarios to run, if None, run all

@router.post("/campaign/run", response_model=ApiResponse[dict])
async def trigger_red_team_campaign(
    trigger: RedTeamTrigger,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin)
):
    """
    Trigger an automated red team campaign in the background.
    """
    campaign = RedTeamCampaign()
    background_tasks.add_task(campaign.run_full_campaign)
    
    return ApiResponse.ok(data={
        "campaign_id": campaign.campaign_id,
        "status": "started",
        "scenarios_count": "All (Default)" if not trigger.scenarios else len(trigger.scenarios)
    })

@router.get("/campaign/history", response_model=ApiResponse[list])
async def get_red_team_history(
    current_user: User = Depends(get_current_admin)
):
    """
    Get history of all red team campaigns.
    """
    report_dir = Path(r"c:\Users\linkage\Desktop\aiproject\docs\red_team")
    history = []
    
    if report_dir.exists():
        for file in report_dir.glob("Summary_*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history.append({
                        "id": data.get("campaign_id"),
                        "total_scenarios": data.get("total_scenarios"),
                        "detection_rate": data.get("detection_rate"),
                        "timestamp": data.get("details", [{}])[0].get("timestamp", "Unknown")
                    })
            except Exception:
                continue
    
    # Sort by ID (timestamp based) desc
    history.sort(key=lambda x: x["id"], reverse=True)
    return ApiResponse.ok(data=history)

@router.get("/campaign/{campaign_id}", response_model=ApiResponse[dict])
async def get_red_team_details(
    campaign_id: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Get details for a specific campaign.
    """
    report_path = Path(r"c:\Users\linkage\Desktop\aiproject\docs\red_team") / f"Summary_{campaign_id}.json"
    
    if not report_path.exists():
        return ApiResponse.error(message="Campaign report not found.")
    
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    return ApiResponse.ok(data=data)
