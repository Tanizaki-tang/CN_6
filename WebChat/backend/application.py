import uvicorn
from fastapi import FastAPI,WebSocket, WebSocketDisconnect, Depends, Request,  File, HTTPException
import CorConfig

import Service.websocket_service as websocket_service
import Service.auth_service as auth_service
import Service.chat_service as chat_service
import Service.db_service as db_service
import os

from Service.websocket_service import ws_manager

app = FastAPI(title="Chat Server",version="1.0")
CorConfig.setupCors(app)

app.include_router(websocket_service.router)
app.include_router(auth_service.router)
app.include_router(chat_service.router)


@app.get("/")
def index():
    """
    根路径测试接口
    """
    return {
        "msg":"Chat Server 服务运行中",
        "author":"Tang",
        "version":"1.0"
    }



if __name__ =="__main__":
    db_service.init_db()
    uvicorn.run(
            app="application:app",
            host="0.0.0.0",
            port=8888,
            reload = True # 开发模式热重载，生产环境关闭
        )