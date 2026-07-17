from fastapi import FastAPI
from pydantic import BaseModel
from backend.app.ml.absa_predictor import ABSAPredictor


app = FastAPI()

predictor = ABSAPredictor()


class ReviewRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {
        "message": "ABSA API RUNNING"
    }


@app.post("/predict")
def predict_review(request: ReviewRequest):
    return predictor.predict(request.text)