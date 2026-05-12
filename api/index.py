from fastapi import FastAPI
app = FastAPI()

@app.get("/api/index")
def hello():
    return {"status": "Python is running!", "file": "api/index.py"}