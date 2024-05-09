import firebase_admin
from fastapi import HTTPException
from fastapi import status
from firebase_admin import credentials
from firebase_admin import auth
from firebase_admin.exceptions import InvalidArgumentError

cred = credentials.Certificate("/code/serviceAccountKey.json")
ai_toys_firebase = firebase_admin.initialize_app(cred, name="ai-toys-firebase")


def verify_token_firebase(uid):
    try:
        # decoded_token = auth.verify_id_token(token, app=ai_toys_firebase)
        decoded_token = auth.get_user(uid, app=ai_toys_firebase)
        # print("decoded_token", decoded_token)
        uid_token = decoded_token.uid
        email_token = decoded_token.email
        # if uid_token == uid and email_token == email:
        if uid_token == uid:
            return decoded_token
        return None
    except InvalidArgumentError as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Signature invalid"
        ) from e


def get_user(uid):
    try:
        return auth.get_user(uid, app=ai_toys_firebase)
    except Exception as e:
        print(e)
        return None


async def get_user_token_firebase(data: dict):
    # token = data.get("token")
    # email = data.get("email")
    uid = data.get("uid")

    if not uid:
        raise HTTPException(status_code=400, detail="Invalid data")

    return verify_token_firebase(uid)
