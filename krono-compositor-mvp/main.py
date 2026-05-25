import uvicorn
from fastapi import FastAPI
from compositor.presentation.api import router

# Initialize FastAPI App
app = FastAPI(
    title="Krono 2.5D Compositor API",
    description="Local MVP for interior visualization compositing.",
    version="0.1.0"
)

# Register our routes
app.include_router(router)

@app.get("/")
def health_check():
    return {"status": "Engine is running!"}

if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8000")
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)