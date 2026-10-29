
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from database import (
    initialize_database,
    create_stock_request,
    get_stock_request,
    get_all_stock_requests,
    update_request_status,
    get_audit_logs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Retail Operations Automation API",
    description="Stock request management and approval workflow",
    version="1.0.0",
    lifespan=lifespan,
)


class StockRequestInput(BaseModel):
    item: str = Field(min_length=2, max_length=100)
    quantity: int = Field(gt=0, le=10000)
    reason: str = Field(min_length=5, max_length=500)


@app.get("/")
def home():
    return {
        "message": "Retail Operations Automation API is running"
    }


@app.post("/requests", status_code=status.HTTP_201_CREATED)
def create_request(request: StockRequestInput):
    request_id = create_stock_request(
        request.item.strip(),
        request.quantity,
        request.reason.strip(),
    )

    return get_stock_request(request_id)


@app.get("/requests")
def list_requests():
    return get_all_stock_requests()


@app.get("/requests/{request_id}")
def retrieve_request(request_id: int):
    request = get_stock_request(request_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found",
        )

    return request


@app.post("/requests/{request_id}/approve")
def approve_request(request_id: int):
    updated = update_request_status(request_id, "Approved")

    if not updated:
        request = get_stock_request(request_id)

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Stock request not found",
            )

        raise HTTPException(
            status_code=409,
            detail="Only pending requests can be approved or rejected",
        )

    return get_stock_request(request_id)


@app.post("/requests/{request_id}/reject")
def reject_request(request_id: int):
    updated = update_request_status(request_id, "Rejected")

    if not updated:
        request = get_stock_request(request_id)

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Stock request not found",
            )

        raise HTTPException(
            status_code=409,
            detail="Only pending requests can be approved or rejected",
        )

    return get_stock_request(request_id)


@app.get("/requests/{request_id}/audit")
def retrieve_audit_logs(request_id: int):
    request = get_stock_request(request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Stock request not found",
        )

    return get_audit_logs(request_id)
