from app.router import agent, context, mongo
from app.setup import setup_app

app = setup_app()

app.include_router(agent.router)
app.include_router(context.router)
app.include_router(mongo.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
