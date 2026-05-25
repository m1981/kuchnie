import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # NEW IMPORT
from fastapi.responses import FileResponse  # NEW IMPORT
from compositor.presentation.api import router

# Initialize FastAPI App
app = FastAPI(
    title="Krono 2.5D Compositor API",
    description="Local MVP for interior visualization compositing.",
    version="0.1.0"
)

# Register our routes
app.include_router(router)

# NEW: Mount the static folder so the browser can access it
app.mount("/static", StaticFiles(directory="static"), name="static")

# NEW: Serve the index.html on the root URL
@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8000")
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)