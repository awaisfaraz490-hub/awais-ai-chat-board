import re
import bcrypt

from fastapi import Request, HTTPException

from database import get_session_user


SESSION_COOKIE_NAME = "docu_session"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ==============================
# PASSWORD HELPERS
# ==============================

def hash_password(plain_password: str) -> str:

    hashed = bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:

    try:

        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

    except ValueError:

        return False


# ==============================
# VALIDATION HELPERS
# ==============================

def is_valid_email(email: str) -> bool:

    return bool(EMAIL_PATTERN.match(email.strip()))


def is_valid_password(password: str) -> bool:

    return len(password) >= 6


# ==============================
# CURRENT USER DEPENDENCIES
# ==============================

def get_current_user(request: Request):
    """
    FastAPI dependency: raises 401 if there is no valid session.
    Use this to protect routes that require login.
    """

    token = request.cookies.get(SESSION_COOKIE_NAME)

    user = get_session_user(token)

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in."
        )

    return user


def get_optional_user(request: Request):
    """
    FastAPI dependency: returns the user if logged in, otherwise None.
    Use this for routes that behave differently but don't require login.
    """

    token = request.cookies.get(SESSION_COOKIE_NAME)

    return get_session_user(token)