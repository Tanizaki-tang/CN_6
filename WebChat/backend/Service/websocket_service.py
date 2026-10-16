import threading
import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from pydantic import BaseModel
from typing import List

#region 模型配置
class UserList(BaseModel):
    userlist: List[str]

class Message(BaseModel):
    name: str
    time:str
    msg:str
    #image :待实现

#endregion

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connection = dict[int,WebSocket]={} #保存所有在线用户

    async def connect(self,user_id:int, ws:WebSocket):
        await ws.accept()
        old = self.active_connection.get(user_id)
        if old and old is not ws:
            try:
                await old.close(code=1000) #1000-正常关闭的状态码
            except Exception:
                pass
            self.active_connection[user_id] =ws

    async def disconnect(self,user_id:int,ws: WebSocket):
        """
        从字典里移除登记，注意不是主动断开连接
        """
        if ws is None or self.active_connection.get(user_id) is ws:
            self.active_connection.pop(user_id,None)    #pop会自建空key情况



ws_manager= ConnectionManager()