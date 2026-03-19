from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import APIRouter, HTTPException

from app.core.database import users_collection
from app.core.security import create_access_token
from app.models.user import UserLoginRequest, UserRegisterRequest


router = APIRouter()


def _hash_password(password: str, salt_hex: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000)
    return dk.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    return secrets.compare_digest(_hash_password(password, salt_hex), password_hash)


@router.post("/register")
def register_user(payload: UserRegisterRequest):
    username_key = payload.username.lower()
    email_key = payload.email.lower()

    existing = users_collection.find_one(
        {"$or": [{"username_key": username_key}, {"email_key": email_key}]}
    )
    if existing:
        if existing.get("username_key") == username_key:
            raise HTTPException(status_code=409, detail="Username already registered")
        raise HTTPException(status_code=409, detail="Email already registered")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(payload.password, salt)

    user_doc = {
        "username": payload.username,
        "username_key": username_key,
        "email": payload.email,
        "email_key": email_key,
        "password_salt": salt,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }
    result = users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access_token = create_access_token(
        subject=user_id,
        extra_claims={"username": payload.username, "email": payload.email},
    )

    return {
        "user": {
            "id": user_id,
            "username": payload.username,
            "email": payload.email,
        },
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Registration successful",
    }


@router.post("/login")
def login_user(payload: UserLoginRequest):
    username_key = payload.username.lower()
    email_key = payload.email.lower()

    user = users_collection.find_one(
        {
            "username_key": username_key,
            "email_key": email_key,
        }
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not _verify_password(payload.password, user.get("password_salt", ""), user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user.get("_id"))
    username = str(user.get("username") or "")
    email = str(user.get("email") or "")
    access_token = create_access_token(
        subject=user_id,
        extra_claims={"username": username, "email": email},
    )

    return {
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
        },
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Login successful",
    }
