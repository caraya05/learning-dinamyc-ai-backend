from fastapi import Depends, HTTPException, Request, status
from bson import ObjectId

from auth.services import auth_access
from core.database import db


async def auth_header(request: Request) -> str | None:
    if authorization := request.headers.get("Authorization"):
        scheme, _, token = authorization.partition(" ")
        if scheme and token and scheme.lower() == "bearer":
            return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Authorization Header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def auth_base(token: str) -> dict:
    if user := await auth_access(token=token):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def auth(token: str = Depends(auth_header)) -> dict:
    return await auth_base(token=token)


async def auth_admin(token: str = Depends(auth_header)) -> dict:
    if user_admin := await auth_base(token=token):
        if (
                user_admin.get("is_superuser")
                and user_admin.get("is_staff")
        ):
            return user_admin
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User is not an admin",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def auth_team(token: str = Depends(auth_header)) -> dict:
    """
    Authenticate user and return team owner's data.
    
    When a team member accesses, returns:
    - Team owner's user data (if plan_type = "team")
    - _id_member: The original requesting user's ID
    
    Returns:
        dict: Team owner data + _id_member field
    """
    # Get current user from token
    if not (current_user := await auth_base(token=token)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get current user's ID
    current_user_id = str(current_user.get("_id"))

    if not current_user.get("plan_type") == "team":
        return current_user

    # Get team_id from current user
    team_id = current_user.get("team_id")

    # Get team from database
    team_db = await db["team"].find_one({"_id": ObjectId(team_id)})

    if not team_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Team not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get team owner's ID
    owner_id = team_db.get("owner_id")

    if not owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Team owner not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get team owner's user data
    owner_user = await db["user"].find_one({"_id": ObjectId(owner_id)})

    if not owner_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Team owner user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert ObjectId to string
    owner_user["_id"] = str(owner_user["_id"])

    # Add _id_member field with current user's ID
    owner_user["_id_member"] = current_user_id

    return owner_user
