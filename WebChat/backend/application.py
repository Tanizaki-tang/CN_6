import uvicorn
from fastapi import FastAPI
import CorConfig
import user_list_controller
import websocket_server

app = FastAPI(title="Chat Server",version="1.0")
CorConfig.setupCors(app)
app.include_router(user_list_controller.router)
app.include_router(websocket_server.router)


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