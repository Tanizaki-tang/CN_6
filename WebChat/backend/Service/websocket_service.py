'''
管理WebSocket的链接与断开，维护在线ws字典
'''

from fastapi import WebSocket, APIRouter
from collections.abc import ItemsView

router = APIRouter(prefix='/ws')

class ConnectionManager:
    def __init__(self):
        self.active_connection : dict[int,WebSocket]={} #保存所有在线用户

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
        if self.active_connection.get(user_id) is ws:
            self.active_connection.pop(user_id,None)    #pop会自建空key情况

    async def kick(self,user_id:int):
        """
        强制下线：摘掉登记并把连接关掉（HTTP /auth/logout 用）
        关连接会触发 WS 端点的 finally，从而真正走一遍下线流程
        """
        old = self.active_connection.pop(user_id,None)
        if old is not None:
            try:
                await old.close(code=1000) #1000-正常关闭的状态码
            except Exception:
                pass

    def  get_active_number(self)->int:
        return len(self.active_connection)

    def get_target_ws(self,target_id:int)-> WebSocket | None:
        return self.active_connection.get(target_id)

    def get_connection_items(self)->ItemsView[int,WebSocket]:
        return self.active_connection.items()


ws_manager= ConnectionManager()

