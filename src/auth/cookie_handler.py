"""
Cookie handling utilities for authentication
"""

from fastapi import Cookie, HTTPException, status
from fastapi.responses import Response
import logging
from auth.services import auth_access

logger = logging.getLogger(__name__)


async def get_current_user_from_cookie(
    access_token_qwestar: str = Cookie(None)
) -> dict:
    """
    Dependency to extract and validate user from cookie.
    
    Args:
        access_token_qwestar: Authentication token from 'access_token_qwestar' cookie
        
    Returns:
        dict: User object with _id, email, username, etc.
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not access_token_qwestar:
        logger.warning("Missing access_token_qwestar cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication cookie found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validate token using existing auth service
        user = await auth_access(access_token_qwestar)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating cookie token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_cookie_no_credentials(
        access_token_qwestar: str = Cookie(None)
) -> dict | None:
    """
    Dependency to extract and validate user from cookie.

    Args:
        access_token_qwestar: Authentication token from 'access_token_qwestar' cookie

    Returns:
        dict: User object with _id, email, username, etc.

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not access_token_qwestar:
        return None

    try:
        # Validate token using existing auth service
        user = await auth_access(access_token_qwestar)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating cookie token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def set_auth_cookie(
    response: Response,
    token: str,
    max_age: int = 3600,
    secure: bool = True,
    httponly: bool = True,
    samesite: str = "lax"
) -> Response:
    """
    Set authentication cookie in response.
    
    Args:
        response: FastAPI Response object
        token: JWT token to store in cookie
        max_age: Cookie expiration time in seconds (default: 1 hour)
        secure: Only send over HTTPS (default: True)
        httponly: Not accessible from JavaScript (default: True)
        samesite: SameSite policy (default: "lax")
        
    Returns:
        Response: Modified response with cookie set
        
    Example:
        response = JSONResponse({"status": "logged in"})
        set_auth_cookie(response, token)
        return response
    """
    response.set_cookie(
        key="access_token_qwestar",
        value=token,
        max_age=max_age,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        path="/"  # Available to all paths
    )
    return response


def remove_auth_cookie(response: Response) -> Response:
    """
    Remove authentication cookie from response (logout).
    
    Args:
        response: FastAPI Response object
        
    Returns:
        Response: Modified response with cookie deleted
        
    Example:
        response = JSONResponse({"status": "logged out"})
        remove_auth_cookie(response)
        return response
    """
    response.delete_cookie(
        key="access_token_qwestar",
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="lax"
    )
    return response


async def get_current_user_from_cookie_or_header(
    access_token_qwestar: str = Cookie(None),
    authorization: str = None
) -> dict:
    """
    Dependency to get user from EITHER cookie OR header Bearer token.
    Useful for supporting both web browsers and API clients.
    
    Args:
        access_token_qwestar: Token from 'access_token_qwestar' cookie
        authorization: Token from 'Authorization: Bearer <token>' header
        
    Returns:
        dict: User object
        
    Raises:
        HTTPException: 401 if both are missing or invalid
    """
    # Try cookie first
    token = access_token_qwestar
    
    # Fall back to header Bearer token
    if not token and authorization:
        try:
            # Extract Bearer token from "Bearer <token>"
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        except Exception:
            pass
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication method provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_access(token)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Cookie configuration
COOKIE_CONFIG = {
    "access_token_qwestar": {
        "name": "access_token_qwestar",
        "max_age": 3600,  # 1 hour
        "secure": True,
        "httponly": True,
        "samesite": "lax",
        "path": "/"
    },
    "refresh_token_qwestar": {
        "name": "refresh_token_qwestar",
        "max_age": 604800,  # 7 days
        "secure": True,
        "httponly": True,
        "samesite": "lax",
        "path": "/"
    }
}

