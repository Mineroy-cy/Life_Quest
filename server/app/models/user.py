from pydantic import BaseModel, field_validator, model_validator
import re


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,24}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = (value or "").strip()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError("Username must be 3-24 chars, letters/numbers/underscore only")
        return username

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = (value or "").strip().lower()
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Please provide a valid email address")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value or ""
        if len(password) < 8 or len(password) > 128:
            raise ValueError("Password must be between 8 and 128 characters")
        if not re.search(r"[A-Za-z]", password):
            raise ValueError("Password must include at least one letter")
        if not re.search(r"\d", password):
            raise ValueError("Password must include at least one number")
        return password

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.password != self.confirm_password:
            raise ValueError("Password confirmation does not match")
        return self


class UserLoginRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = (value or "").strip()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError("Username must be 3-24 chars, letters/numbers/underscore only")
        return username

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = (value or "").strip().lower()
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Please provide a valid email address")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value or ""
        if len(password) < 8 or len(password) > 128:
            raise ValueError("Password must be between 8 and 128 characters")
        return password
