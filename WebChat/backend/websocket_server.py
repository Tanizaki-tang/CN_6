import threading
import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from Model import UserList, Message

router = APIRouter()

session_map :dict[str,WebSocket] ={} #保存所有在线用户
lock = threading.Lock() #涉及到线程安全，得学

def show_user_list():
    """
    控制台打印在线用户
    """
    print("------------------------------------------")
    print("当前在线用户")
    print("------------------------------------------")
    for username in session_map.keys():
        print(username)
    print("------------------------------------------")
    print()

def set_user_list()->str:
    """
    组装在线用户列表JSON字符串
    进行了信息校验和过滤，防止前端乱传字段
    """
    user_name_list = list(session_map.keys())
    obj = UserList(userlist=user_name_list)  #pydanic自动生成构造函数
    return json.dumps(obj.model_dump())

async def send_all_message(message:str):
    """
    广播消息给全部在线客户端
    """
    for ms in session_map.values():
        try:
            await ms.send_text(message) #?
        except Exception as e:
            print(e)



@router.websocket("/socket/{username}")
async def websocket_endpoint(websocket :WebSocket ,username:str):
    """
    对外暴露的服务入口函数；管理用户的加入及退出
    """
    await websocket.accept()

    with lock:
        is_exist = username in session_map
        if not is_exist:
            print(f"{username}加入了聊天室")
            session_map[username] =websocket
            await send_all_message(set_user_list())
            show_user_list()

    try:
        #循环接收客户端信息
        while True:
            data =await websocket.receive_text()
            msg_dict = json.loads(data) # json转dict
            msg_obj = Message(**msg_dict)
            await send_all_message(json.dumps(msg_obj.model_dump())) #model_dump()：把pydantic对象转dict

    except WebSocketDisconnect: #客户端主动断开连接的内置异常
        with lock:
            if username is not None and username in session_map:
                print(f"{username}退出了聊天室")
                del session_map[username]
                await send_all_message(set_user_list())
                show_user_list()

    except Exception as e:
        print("发生异常")
        print(e)


