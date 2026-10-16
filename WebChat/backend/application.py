import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import CorConfig
import Service.websocket_service as websocket_service
import Service.auth_service as auth_service
import Service.chat_service as chat_service
from Service.db_service import init_db
from Service.paths import UPLOAD_DIR

app = FastAPI(title="Chat Server",version="1.0")
CorConfig.setupCors(app)

#建表放在模块里(不是__main__)：uvicorn 热重载的子进程只 import 模块，不会跑 __main__
init_db()

#upload_img 返回的是 /static/uploads/xxx，所以把 static/ 目录挂到 /static
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR.parent)), name="static")

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
    #必须在 WebChat/backend 目录下运行：python application.py
    uvicorn.run(
            app="application:app",
            host="0.0.0.0",
            port=8888,
            reload = True # 开发模式热重载，生产环境关闭
        )
