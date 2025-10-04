from app.schema.context import StreamlitSession
from fastapi import APIRouter

router = APIRouter(prefix="/context", tags=["context"])

@router.post("/session")
async def create_session_endpoint(session: StreamlitSession):
    pass


@router.get("/session/{session_id}")
async def get_session_endpoint(session_id: str):
    pass