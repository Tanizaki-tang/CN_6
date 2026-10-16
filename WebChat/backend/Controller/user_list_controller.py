from fastapi import APIRouter

from WebChat.backend.Service.websocket_service import session_map

router = APIRouter(prefix="/list")

@router.get("/{username}")
def get_username(username:str):
    """
    判断用户是否在聊天室
    Param:
        username: 用户名路径参数

    return:
        {:isEmpty" : bool,"isExist" : bool}
    """
    isEmpty=len(session_map)==0
    result={
        "isEmpty":isEmpty,
        "isExist": False
    }
    if not isEmpty:
        result["isExist"] = username in session_map
    return result
