from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api import marketplaces, car_scraping, regression, export

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(marketplaces.router)
app.include_router(car_scraping.router)
app.include_router(regression.router)
app.include_router(export.router, prefix="/api", tags=["export"])
