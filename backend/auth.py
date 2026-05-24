from fastapi import APIRouter, Response, Request, Depends
from pydantic import BaseModel
from pymongo import MongoClient

from google.oauth2 import id_token
from google.auth.transport import requests

from jose import jwt, JWTError

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from datetime import datetime, timedelta, timezone

import os
import re

# =========================
# ROUTER
# =========================

router = APIRouter()

# =========================
# DATABASE
# =========================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://<user>:<pass>@cluster.mongodb.net/"
)

client = MongoClient(MONGO_URI)

db = client["chatsun"]

users = db["users"]

# =========================
# SECURITY
# =========================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change_this_in_production"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_DAYS = 30

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "YOUR_GOOGLE_CLIENT_ID"
)

ph = PasswordHasher()

# =========================
# MODELS
# =========================

class RegisterModel(BaseModel):
    full_name: str
    email: str
    password: str
    user_id: str
    phone_number: str = ""

class LoginModel(BaseModel):
    email: str
    password: str

class GoogleToken(BaseModel):
    token: str

# =========================
# VALIDATION
# =========================

def validate_email(email):

    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    return re.match(pattern, email)

def validate_user_id(user_id):

    pattern = r"^[a-z0-9_]{3,20}$"

    return re.match(pattern, user_id)

# =========================
# JWT
# =========================

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        days=ACCESS_TOKEN_EXPIRE_DAYS
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

# =========================
# GET CURRENT USER
# =========================

def get_current_user(request: Request):

    token = request.cookies.get(
        "access_token"
    )

    if not token:
        return None

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("email")

        if not email:
            return None

        user = users.find_one({
            "email": email
        })

        return user

    except JWTError:
        return None

# =========================
# REGISTER
# =========================

@router.post("/register")
async def register(
    data: RegisterModel,
    response: Response
):

    full_name = data.full_name.strip()

    email = data.email.strip().lower()

    password = data.password.strip()

    user_id = data.user_id.strip().lower()

    # -------------------------
    # VALIDATION
    # -------------------------

    if (
        not full_name or
        not email or
        not password or
        not user_id
    ):
        return {
            "success": False,
            "message": "All fields required"
        }

    if len(full_name) < 2:
        return {
            "success": False,
            "message": "Invalid full name"
        }

    if not validate_email(email):
        return {
            "success": False,
            "message": "Invalid email"
        }

    if not validate_user_id(user_id):
        return {
            "success": False,
            "message": "Invalid user id"
        }

    if len(password) < 6:
        return {
            "success": False,
            "message":
            "Password must be at least 6 characters"
        }

    # -------------------------
    # EXIST CHECK
    # -------------------------

    if users.find_one({
        "email": email
    }):
        return {
            "success": False,
            "message": "Email already exists"
        }

    if users.find_one({
        "user_id": user_id
    }):
        return {
            "success": False,
            "message": "User ID already taken"
        }

    # -------------------------
    # HASH PASSWORD
    # -------------------------

    password_hash = ph.hash(password)

    # -------------------------
    # CREATE USER
    # -------------------------

    user_data = {

        "full_name": full_name,

        "email": email,

        "user_id": user_id,

        "password_hash": password_hash,

        "auth_type": "password",

        "created_at":
            datetime.now(timezone.utc),
        "phone_number":data.phone_number,
        
    }

    users.insert_one(user_data)

    # -------------------------
    # CREATE JWT
    # -------------------------

    token = create_access_token({
        "email": email
    })

    # -------------------------
    # SET COOKIE
    # -------------------------

    response.set_cookie(

        key="access_token",

        value=token,

        httponly=True,

        secure=True,

        path="/",

        samesite="none",

        max_age=60 * 60 * 24 * 30
    )

    return {

        "success": True,

        "user": {

            "full_name": full_name,

            "email": email,

            "user_id": user_id
        }
    }

# =========================
# LOGIN
# =========================

@router.post("/login")
async def login(
    data: LoginModel,
    response: Response
):

    email = data.email.strip().lower()

    password = data.password.strip()

    if not email or not password:
        return {
            "success": False,
            "message": "All fields required"
        }

    user = users.find_one({
        "email": email
    })

    if not user:
        return {
            "success": False,
            "message": "Wrong email or password"
        }

    if user.get("auth_type") == "google":
        return {  "success": False, "message": "This account uses Google Sign-In"}


    try:

        ph.verify(
            user["password_hash"],
            password
        )

    except VerifyMismatchError:

        return {
            "success": False,
            "message": "Wrong email or password"
        }

    token = create_access_token({
        "email": email
    })

    response.set_cookie(

        key="access_token",

        value=token,

        httponly=True,

        secure=True,

        path="/",

        samesite="none",

        max_age=60 * 60 * 24 * 30
    )

    return {

        "success": True,

        "user": {

            "full_name":
                user["full_name"],

            "email":
                user["email"],

            "user_id":
                user["user_id"]
        }
    }

# =========================
# GOOGLE LOGIN
# =========================

@router.post("/google-login")
async def google_login(
    data: GoogleToken,
    response: Response
):

    try:

        info = id_token.verify_oauth2_token(

            data.token,

            requests.Request(),

            GOOGLE_CLIENT_ID
        )

        email = info["email"]

        full_name = info.get(
            "name",
            "Google User"
        )

        picture = info.get(
            "picture",
            ""
        )

        user = users.find_one({
            "email": email
        })

        # -------------------------
        # CREATE USER IF NOT EXISTS
        # -------------------------

        if not user:

            base_user_id = (
                email
                .split("@")[0]
                .lower()
                .replace(" ", "_")
            )

            user_id = base_user_id

            counter = 1

            while users.find_one({
                "user_id": user_id
            }):

                user_id = (
                    f"{base_user_id}{counter}"
                )

                counter += 1

            user_data = {

                "full_name":
                    full_name,

                "email":
                    email,

                "user_id":
                    user_id,

                "profile_picture":
                    picture,
                "phone_number": "",


                "auth_type":
                    "google",

                "created_at":
                    datetime.now(
                        timezone.utc
                    )
            }

            users.insert_one(
                user_data
            )

            user = user_data

        # -------------------------
        # JWT
        # -------------------------

        token = create_access_token({
            "email": email
        })

        response.set_cookie(

            key="access_token",

            value=token,

            httponly=True,

            secure=True,

            path="/",

            samesite="none",

            max_age=60 * 60 * 24 * 30
        )

        return {

            "success": True,

            "user": {

                "full_name":
                    user["full_name"],

                "email":
                    user["email"],

                "user_id":
                    user["user_id"]
            }
        }

    except Exception as e:

        print(e)

        return {
            "success": False,
            "message": "Google login failed"
        }

# =========================
# GET ME
# =========================

@router.get("/me")
async def get_me(
    request: Request
):

    user = get_current_user(
        request
    )

    if not user:

        return {
            "success": False
        }

    return {

        "success": True,

        "user": {

            "full_name":
                user["full_name"],

            "email":
                user["email"],
            "phone_number":
            user.get( "phone_number",  ""  ),

            "user_id":
                user["user_id"],
            "profile_picture":
    user.get("profile_picture", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjoowYAeUbwx01s1wuzsFwoaoONtdK2qCu5Yb50rRzxQ&s=10")
        }
    }

# =========================
# LOGOUT
# =========================

@router.post("/logout")
async def logout(
    response: Response
):

    response.delete_cookie(

        key="access_token",

        httponly=True,

        secure=True,

        samesite="none"
    )

    return {
        "success": True
    }

# =========================
# DELETE ACCOUNT
# =========================

@router.delete("/delete-account")
async def delete_account(
    request: Request,
    response: Response
):

    user = get_current_user(
        request
    )

    if not user:

        return {
            "success": False,
            "message": "Unauthorized"
        }

    users.delete_one({
        "email": user["email"]
    })

    response.delete_cookie(
        "access_token"
    )

    return {
        "success": True
    }
