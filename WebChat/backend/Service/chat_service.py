from Service.websocket_service import ConnectionManager
from fastapi import WebSocket

class ChatManager:
    def __init__(self, connect_mg:ConnectionManager,session_factory):
        pass
    async def _send(self, ws:WebSocket, msg_json:str)-> bool:
        try:
            await ws.send_text(msg_json)
            return True
        except Exception:
            return False

    async def enter(self, user_id, ws)-> bool:
        ...

    async def leave(self, user_id, ws)-> bool:
        ...

    def history(self,
                uid,
                target_uid:int =None,
                group_id:int=None)->list[dict]:
        ...


    async def broadcast(self, msg_json:str):
        for uid,ws in list(self.active_connection.items()):
            if not await self._send(ws, msg_json):
                self.disconnect(uid,ws)

    async def broadcast_online(self,db):
        """
        广播全体用户在线状态
        """
        #查用户属于业务层，不能放数据层
        online_users= db.query(DBUser).filter(DBUser.is_online.is_(True)).all()
        await self.broadcast(json.dumps({
            "type": "online_list",
            "users": [{"id":u.id,"name":u.username} for u in online_users]
        }))

    async def send_private_msg(self, target_user_id: int , msg_json: str):
        ws = self.active_connection.get(target_user_id)
        if ws is None:
            return False
        if not await self._send(target_user_id,msg_json):
            self.disconnect(target_user_id,ws)
        return True