from contextlib import asynccontextmanager
import sqlite3

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from jwt import InvalidTokenError

from database import (
    initialize_database,
    create_user,
    get_user_by_username,
    create_stock_request,
    get_stock_request,
    get_all_stock_requests,
    update_request_status,
    get_audit_logs,
)

from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Retail Operations Automation API",
    description="Retail stock management with JWT authentication and role-based access",
    version="2.0.0",
    lifespan=lifespan,
)


bearer_scheme = HTTPBearer(auto_error=False)


# ==========================================
# REQUEST MODELS
# ==========================================

class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    
    
class ManagerSetupInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class StockRequestInput(BaseModel):
    item: str = Field(min_length=2, max_length=100)
    quantity: int = Field(gt=0, le=10000)
    reason: str = Field(min_length=5, max_length=500)


# ==========================================
# AUTHENTICATION AND AUTHORIZATION
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)

        user_id = int(payload["sub"])

    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_username(payload.get("username", ""))

    if user is None or user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_employee_or_manager(
    current_user=Depends(get_current_user),
):
    return current_user


def require_manager(
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager permissions required",
        )

    return current_user


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Retail Operations Automation API is running",
        "authentication": "JWT",
        "authorization": "Role-Based Access Control",
    }


# ==========================================
# EMPLOYEE REGISTRATION
# ==========================================

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_input: RegisterInput):
    username = user_input.username.strip().lower()

    if len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must contain at least 3 non-whitespace characters",
        )

    if get_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    password_digest = hash_password(user_input.password)

    try:
        user_id = create_user(
            username,
            password_digest,
            "employee",
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    return {
        "message": "Employee account created successfully",
        "user_id": user_id,
        "username": username,
        "role": "employee",
    }

# ==========================================
# LOGIN
# ==========================================

@app.post("/login")
def login_user(login_input: LoginInput):
    username = login_input.username.strip().lower()

    user = get_user_by_username(username)

    if user is None or not verify_password(
        login_input.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in_minutes": 30,
    }


# ==========================================
# CURRENT USER
# ==========================================

@app.get("/me")
def get_my_profile(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
    }


# ==========================================
# STOCK REQUEST CREATION
# ==========================================

@app.post("/requests", status_code=status.HTTP_201_CREATED)
def create_request(
    request: StockRequestInput,
    current_user=Depends(require_employee_or_manager),
):
    item = request.item.strip()
    reason = request.reason.strip()

    if len(item) < 2:
        raise HTTPException(
            status_code=422,
            detail="Item must contain at least 2 non-whitespace characters",
        )

    if len(reason) < 5:
        raise HTTPException(
            status_code=422,
            detail="Reason must contain at least 5 non-whitespace characters",
        )

    request_id = create_stock_request(
        item,
        request.quantity,
        reason,
    )

    return get_stock_request(request_id)


# ==========================================
# VIEW STOCK REQUESTS
# ==========================================

@app.get("/requests")
def list_requests(
    current_user=Depends(require_employee_or_manager),
):
    return get_all_stock_requests()


@app.get("/requests/{request_id}")
def retrieve_request(
    request_id: int,
    current_user=Depends(require_employee_or_manager),
):
    request = get_stock_request(request_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found",
        )

    return request


# ==========================================
# MANAGER-ONLY APPROVAL
# ==========================================

@app.post("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    manager=Depends(require_manager),
):
    return change_request_status(request_id, "Approved")


@app.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    manager=Depends(require_manager),
):
    return change_request_status(request_id, "Rejected")


def change_request_status(request_id: int, new_status: str):
    updated = update_request_status(request_id, new_status)

    if not updated:
        request = get_stock_request(request_id)

        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock request not found",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending requests can be approved or rejected",
        )

    return get_stock_request(request_id)


# ==========================================
# AUDIT HISTORY
# ==========================================

@app.get("/requests/{request_id}/audit")
def retrieve_audit_logs(
    request_id: int,
    current_user=Depends(require_employee_or_manager),
):
    request = get_stock_request(request_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found",
        )

    return get_audit_logs(request_id)
