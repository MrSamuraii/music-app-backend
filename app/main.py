from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.database import Base, engine
from app.routers import auth, tracks, playlists, friends, chats, presence, artists, app_info

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Music App API")

# Стандартный CORS-мидлвар должен стоять выше всех остальных
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tracks.router)
app.include_router(playlists.router)
app.include_router(friends.router)
app.include_router(chats.router)
app.include_router(presence.router)
app.include_router(artists.router)
app.include_router(app_info.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "music-app-backend"}