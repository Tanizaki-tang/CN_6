'''
管理用户注册和登录
'''
from sqlalchemy.orm import Session
from fastapi import APIRouter,Form,HTTPException,Depends
from Service.db_service import get_db,DBUser
from Service.websocket_service import ws_manager
import bcrypt

router = APIRouter(prefix="/auth")

# bcrypt 只取前 72 字节；超长时 bcrypt 4.x 会直接 raise ValueError，所以先挡住
MAX_PW_BYTES = 72

def hash_password(pw:str)->str:
    """bcrypt 每次自带随机 salt，返回值里已经含 salt+cost，可直接入库"""
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(input_pw:str, real_pw_hash:str)->bool:
    try:
        return bcrypt.checkpw(input_pw.encode("utf-8"), real_pw_hash.encode("utf-8"))
    except ValueError:      # 库里存的不是合法 bcrypt 串（脏数据/旧格式）→ 一律当验证失败
        return False

@router.post("/register")
async def register(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    """
    注册新用户
    """
    username = username.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password.encode("utf-8")) > MAX_PW_BYTES:
        raise HTTPException(status_code=400, detail=f"密码太长（最多 {MAX_PW_BYTES} 字节）")
    exist = db.query(DBUser).filter(DBUser.username == username).first()
    if exist: raise HTTPException(status_code=400, detail="用户名已存在")
    new_user = DBUser(username=username, hashed_pw=hash_password(password))
    db.add(new_user)
    db.commit()
    return {"msg":"注册成功"}

@router.post('/login')
async def login(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.username == username.strip()).first()
    if not user or not verify_password(password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="账号密码错误")
    return {"uid": user.id, "name":user.username}

# 登出
@router.post("/logout/{uid}")
async def logout(uid:int, db:Session=Depends(get_db)):
    user = db.get(DBUser, uid)
    if user:
        user.is_online = False
        db.commit()
        #kick 会摘掉登记并关连接；WS 端点的 finally 会再走一遍置offline+广播
        await ws_manager.kick(uid)
    return {"msg":"已下线"}
