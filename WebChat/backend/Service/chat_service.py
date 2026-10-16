from fastapi import WebSocket,APIRouter,HTTPException,File,WebSocketDisconnect,UploadFile,Depends
import uuid
import json
import os
import aiofiles
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import ValidationError
from Model import UserList,Message
from Service.db_service import DBUser,DBMessage,get_db,session_scope,SessionLocal,utc_now
from Service.websocket_service import ws_manager
from Service.log_service import get_logger
from Service.paths import UPLOAD_DIR

logger=get_logger(__name__)

ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_IMG_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix='/chat')


async def _send(ws:WebSocket, msg_json:str)-> bool:
    '''发送消息'''
    try:
        await ws.send_text(msg_json)
        return True
    except Exception:
        logger.debug("发送失败，连接可能已经断开", exc_info=True)
        return False


async def broadcast(msg_json:str):
    '''
    广播消息发送器
    '''
    for uid,ws in list(ws_manager.get_connection_items()):
        if not await _send(ws, msg_json):
            await ws_manager.disconnect(uid,ws)

async def broadcast_online():
    """
    广播全体用户在线状态
    """
    #在线名单以 ws_manager 的注册表为准：进程被kill时 DBUser.is_online 会留下幽灵状态
    uids = [uid for uid,_ in list(ws_manager.get_connection_items())]
    names = []
    if uids:
        with SessionLocal() as db:                 # 只读，用完即关
            names = [u.username for u in
                     db.query(DBUser).filter(DBUser.id.in_(uids)).all()]
    # 出了 with 才用 names —— 这时候是普通 list[str]，不是 ORM 对象
    await broadcast(UserList(userlist=names).model_dump_json())

async def send_private_msg(target_uid: int , msg_json: str)-> bool:
    '''发送私聊消息；对方不在线返回 False'''
    ws = ws_manager.get_target_ws(target_uid)
    if ws is None:
        return False
    if not await _send(ws,msg_json):
        await ws_manager.disconnect(target_uid,ws)
        return False
    return True

async def send_group_msg(group_id:int, msg_json:str):
    '''
    发送群聊消息
    DBGroup 目前只有组名、没有成员表，所以先按"广播给所有在线连接"处理；
    以后加了成员表，把 broadcast 换成按成员逐个 _send 即可
    '''
    logger.info("群聊消息 group_id=%s，当前没有成员表，广播给全部在线用户", group_id)
    await broadcast(msg_json)

@router.post("/post/upload_img")
async def upload_img(file:UploadFile=File(...)):
    '''发送图片'''
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMG_EXT:
        raise HTTPException(status_code=400, detail="只支持 png/jpg/jpeg/gif/webp/bmp 图片")
    data = await file.read()
    await file.close()
    if len(data) > MAX_IMG_BYTES:
        raise HTTPException(status_code=413, detail=f"图片不能超过 {MAX_IMG_BYTES // 1024 // 1024}MB")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # 用随机名，避免路径穿越(../../)和同名文件互相覆盖
    filename = f"{uuid.uuid4().hex}{ext}"
    async with aiofiles.open(UPLOAD_DIR / filename,'wb') as f:
        await f.write(data)
    return {"img_url": f"/static/uploads/{filename}"}


@router.get("/get/history")
async def get_history(uid:int, target_uid:Optional[int]=None, group_id:Optional[int]=None, db:Session=Depends(get_db)):
    if target_uid is not None:
        #私聊：A发给B 或者 B发给A
        q = db.query(DBMessage).filter( ((DBMessage.sender_id==uid)&(DBMessage.receiver_id==target_uid)) | ((DBMessage.sender_id==target_uid)&(DBMessage.receiver_id==uid)) )
    elif group_id is not None:
        q = db.query(DBMessage).filter(DBMessage.group_id == group_id)
    else:
        # 不限定会话会把所有人的私聊都返回给调用方
        raise HTTPException(status_code=400, detail="必须指定 target_uid 或 group_id")
    msgs = q.order_by(DBMessage.create_time).all()
    res = []
    for m in msgs:
        sender = db.get(DBUser, m.sender_id)
        res.append({
            "sender_id":m.sender_id,
            "sender_name":sender.username if sender else "未知用户",
            "content":m.content,
            "img_url":m.img_url,
            "time":str(m.create_time)
        })
    return res


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id:int):
    with session_scope() as db:
        user = db.get(DBUser, user_id)
        if user is None: 
            await ws.accept()
            await ws.close(code=1008)
            return
        username = user.username          # ★ 会话还活着时把值取出来
        user.is_online = True
        db.commit()

    await ws_manager.connect(user_id, ws)

    try: #消息循环
        await broadcast_online()   #放在try内：它抛错时 finally 也要能清掉登记
        while True:
            raw = await ws.receive_text()

            try:
                data = Message.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as e:
                #丢弃脏消息要留痕，否则前端"发了没反应"根本查不出来
                logger.warning("丢弃无法解析的消息 user_id=%s err=%s raw=%.200s", user_id, e, raw)
                continue #校验失败，直接丢弃消息

            with session_scope() as db:
                db.add(DBMessage(
                    sender_id=user_id,
                    receiver_id=data.target_uid if data.msg_type == "private" else None,
                    group_id=data.group_id if data.msg_type == "group" else None,
                    content=data.content,
                    img_url=data.img_url,
                ))

            send_data = json.dumps({
                "name": username,
                #和 DBMessage.create_time 用同一个时间基准(UTC)
                "time": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                "msg": data.content if data.content else data.img_url,
            })

            if data.msg_type == "private":
                await send_private_msg(data.target_uid, send_data)
                if data.target_uid != user_id:
                    # 回显给自己，否则发送方要刷新页面才看得到自己刚发的消息
                    await send_private_msg(user_id, send_data)
            else:
                await send_group_msg(data.group_id, send_data)
    except WebSocketDisconnect:
        pass
    finally:
        # 用 finally：连接因任何原因断掉都要下线，不能只在 WebSocketDisconnect 时清
        await ws_manager.disconnect(user_id, ws)
        if ws_manager.get_target_ws(user_id) is None:     # N5：只有真下线才写库
            with session_scope() as db:
                u = db.get(DBUser, user_id)
                if u is not None:
                    u.is_online = False
            await broadcast_online()

