from fastapi import WebSocket,APIRouter,HTTPException,File,Form,WebSocketDisconnect,UploadFile,Depends
import uuid
import json
import os
import aiofiles
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import ValidationError
from Model import UserList,OnlineUser,Message
from Service.db_service import DBUser,DBMessage,DBGroup,DBGroupMember,get_db,session_scope,SessionLocal,utc_now
from Service.websocket_service import ws_manager
from Service.log_service import get_logger
from Service.paths import UPLOAD_DIR

logger=get_logger(__name__)

ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_IMG_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix='/chat')


async def _send(ws:WebSocket, msg_json:str)-> bool:
    '''发送消息'''
    if ws is None:
        return False
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
    users: list[OnlineUser] = []
    if uids:
        with SessionLocal() as db:                 # 只读，用完即关
            rows = db.query(DBUser).filter(DBUser.id.in_(uids)).all()
            # 出了 with 才用 rows —— 这时候取出来的都是普通值，不是 ORM 对象
            users = [OnlineUser(uid=u.id, name=u.username) for u in rows]
    #users 带 uid，前端要它才能填 target_uid；userlist 保留给旧前端
    await broadcast(UserList(userlist=[u.name for u in users], users=users).model_dump_json())

async def send_private_msg(target_uid: int , msg_json: str)-> bool:
    '''发送私聊消息；对方不在线返回 False'''
    ws = ws_manager.get_target_ws(target_uid)
    if ws is None:
        return False
    if not await _send(ws,msg_json):
        await ws_manager.disconnect(target_uid,ws)
        return False
    return True

def _member_ids(db:Session, group_id:int) -> list[int]:
    '''群成员 uid 列表'''
    rows = db.query(DBGroupMember.user_id).filter(DBGroupMember.group_id==group_id).all()
    return [r[0] for r in rows]


def _member_count(db:Session, group_id:int) -> int:
    return db.query(DBGroupMember).filter(DBGroupMember.group_id==group_id).count()


def _is_member(db:Session, group_id:int, uid:int) -> bool:
    return db.query(DBGroupMember).filter(
        DBGroupMember.group_id==group_id, DBGroupMember.user_id==uid
    ).first() is not None


async def send_group_msg(group_id:int, msg_json:str, member_ids:Optional[list[int]]=None):
    '''
    发送群聊消息：只发给群成员
    member_ids 由调用方从数据库里查好传进来，避免在每发一条消息时再查一次库
    '''
    if member_ids is None:
        with SessionLocal() as db:
            member_ids = _member_ids(db, group_id)
    for uid in member_ids:
        ws = ws_manager.get_target_ws(uid)
        if ws is not None and not await _send(ws, msg_json):
            await ws_manager.disconnect(uid, ws)


async def send_group_system(group_id:int, content:str, member_ids:Optional[list[int]]=None):
    '''
    给群成员发一条系统提示(有人加入/退出)
    用 sender_id=None + system=True 与普通消息区分，前端会把它渲染成居中的灰条
    '''
    msg_json = json.dumps({
        "sender_id": None,
        "system": True,
        "name": "系统",
        "time": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        "msg": content,
        "group_id": group_id,
    })
    await send_group_msg(group_id, msg_json, member_ids)


def _group_info(db:Session, g:DBGroup, uid:Optional[int]) -> dict:
    return {
        "group_id": g.id,
        "group_name": g.group_name,
        "owner_id": g.owner_id,
        "member_count": _member_count(db, g.id),
        "is_member": False if uid is None else _is_member(db, g.id, uid),
    }


#region 群聊：列表 / 发现 / 建群 / 加入 / 退出
#改造前这里只有"建群"和"全部群列表"，没有成员表：
#  群聊 = 公共频道，任何在线用户都能收到所有群消息，前端也无从"加入"某个群。
#现在有了 group_members 表：群消息只发给成员，历史也只对成员开放。
@router.get("/get/groups")
async def get_groups(uid:Optional[int]=None, db:Session=Depends(get_db)):
    '''我加入的群（不传 uid 则返回全部群，兼容旧调用）'''
    q = db.query(DBGroup)
    if uid is not None:
        ids = [r[0] for r in db.query(DBGroupMember.group_id).filter(DBGroupMember.user_id==uid).all()]
        if not ids:
            return []
        q = q.filter(DBGroup.id.in_(ids))
    rows = q.order_by(DBGroup.id).all()
    return [_group_info(db, g, uid) for g in rows]


@router.get("/get/groups/discover")
async def discover_groups(uid:Optional[int]=None, db:Session=Depends(get_db)):
    '''
    发现群聊：列出全部群并标注"我是否已在群里"，前端据此显示"进入"还是"加入"
    这个群聊没有邀请/审批机制，所以直接给加入按钮
    '''
    rows = db.query(DBGroup).order_by(DBGroup.id).all()
    return [_group_info(db, g, uid) for g in rows]


@router.post("/post/group")
async def create_group(uid:int=Form(), group_name:str=Form(), db:Session=Depends(get_db)):
    '''建群：建群者自动成为第一个成员(否则建完自己都进不去)'''
    if db.get(DBUser, uid) is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    name = group_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="群名称不能为空")
    group = DBGroup(group_name=name, owner_id=uid)
    db.add(group)
    db.commit()
    db.refresh(group)   #要拿自增的 id
    db.add(DBGroupMember(group_id=group.id, user_id=uid))
    db.commit()
    return _group_info(db, group, uid)


@router.post("/post/group/join")
async def join_group(uid:int=Form(), group_id:int=Form(), db:Session=Depends(get_db)):
    '''加入群聊：重复点不算错(幂等)'''
    if db.get(DBUser, uid) is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    group = db.get(DBGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="群聊不存在")
    if not _is_member(db, group_id, uid):
        db.add(DBGroupMember(group_id=group_id, user_id=uid))
        db.commit()
        #先给"已经在群里的人"发提示，再把新成员算进去
        await send_group_system(group_id, f"{db.get(DBUser, uid).username} 加入了群聊")
    return _group_info(db, group, uid)


@router.post("/post/group/leave")
async def leave_group(uid:int=Form(), group_id:int=Form(), db:Session=Depends(get_db)):
    '''
    退出群聊
    注意要先发系统提示再删成员：删完再算成员列表的话，退出的人收不到那条提示
    '''
    group = db.get(DBGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="群聊不存在")
    if group.owner_id == uid:
        raise HTTPException(status_code=400, detail="群主不能退出自己的群，可以改让管理员来解散")
    member = db.query(DBGroupMember).filter(
        DBGroupMember.group_id==group_id, DBGroupMember.user_id==uid
    ).first()
    if member is not None:
        user = db.get(DBUser, uid)
        await send_group_system(group_id, f"{user.username if user else uid} 退出了群聊")
        db.delete(member)
        db.commit()
    return _group_info(db, group, uid)
#endregion

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
        #群历史只对成员开放，否则"群聊"等于公开的
        if not _is_member(db, group_id, uid):
            raise HTTPException(status_code=403, detail="你不在这个群里")
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
                "sender_id": user_id,   #前端靠它把消息归到正确的会话(私聊/群聊)
                "name": username,
                #和 DBMessage.create_time 用同一个时间基准(UTC)
                "time": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                "msg": data.content if data.content else data.img_url,
                #回执带上目标：私聊带 target_uid、群聊带 group_id。
                #不带的话前端在"自己刚发的那个会话不是当前打开的会话"时无法把回显归位，
                #只能瞎猜或直接丢弃
                "target_uid": data.target_uid if data.msg_type == "private" else None,
                "group_id": data.group_id if data.msg_type == "group" else None,
            })

            if data.msg_type == "private":
                await send_private_msg(data.target_uid, send_data)
                if data.target_uid != user_id:
                    # 回显给自己，否则发送方要刷新页面才看得到自己刚发的消息
                    await send_private_msg(user_id, send_data)
            else:
                #不在群里就不能往群里发：校验放在这里，HTTP 接口和 WS 是两条路
                with SessionLocal() as db:
                    if not _is_member(db, data.group_id, user_id):
                        logger.warning("非群成员发群消息被拦下 user_id=%s group_id=%s", user_id, data.group_id)
                        await _send(ws_manager.get_target_ws(user_id), json.dumps({
                            "sender_id": None, "system": True, "name": "系统",
                            "time": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                            "msg": "你不在这个群里，发送失败", "group_id": data.group_id,
                        }))
                        continue
                    member_ids = _member_ids(db, data.group_id)
                await send_group_msg(data.group_id, send_data, member_ids)
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

