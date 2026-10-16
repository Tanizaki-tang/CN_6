import uvicorn
from fastapi import FastAPI,WebSocket, WebSocketDisconnect, Depends, Request, Form, UploadFile, File, HTTPException
import CorConfig
import WebChat.backend.Controller.user_list_controller as user_list_controller
import WebChat.backend.Service.websocket_service as websocket_service
import os

from Service.websocket_service import ws_manager

app = FastAPI(title="Chat Server",version="1.0")
CorConfig.setupCors(app)
app.include_router(user_list_controller.router)
app.include_router(websocket_service.router)


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





def main():
    """
    启动Web服务
    """
    uvicorn.run(
        app="application:app",
        host="0.0.0.0",
        port=8888,
        reload = True # 开发模式热重载，生产环境关闭
    )

if __name__ =="__main__":
    main()