from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.agent import AgentExecuteRequest
from services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/execute")
async def execute_agent(request: AgentExecuteRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    service = AgentService(db)
    return await service.orchestrate_execution(
        guild_id=request.guild_id,
        discord_channel_id=request.discord_channel_id,
        prompt=request.prompt,
        background_tasks=background_tasks
    )
