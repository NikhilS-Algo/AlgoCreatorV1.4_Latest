from fastapi import FastAPI
from dotenv import load_dotenv
# from extraction.extraction_routes import router as extraction_router
from retrieval.retrieval_routes import router as retrieval_router
# from utils.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
#import tagGenaration
from fastapi.staticfiles import StaticFiles

import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust the origin as needed
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(extraction_router, prefix="/extraction")
app.include_router(retrieval_router, prefix="/retrieval")

app.mount("/static", StaticFiles(directory="static"), name="static")

# app.include_router(auth_router, prefix="/auth")
#app.include_router(tagGenaration.myrouter)

@app.get("/")
async def root():
    return {"message": "Hello World"}
  
