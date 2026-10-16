'''
管理用户注册和登录
'''
from sqlalchemy.orm import Session
from fastapi import APIRouter,Form,HTTPException,Depends
from Service.db_service import get_db,DBUser
from Service.websocket_service import ws_manager
from passlib.context import CryptContext

router = APIRouter(prefix="/auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(input_pw:str, real_pw_hash:str)->bool:
    return pwd_context.verify(input_pw, real_pw_hash)

def hash_password(pw:str)->str:
    return pwd_context.hash(pw)

@router.post("/register")
async def register(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    """
    注册新用户
    """
    username = username.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
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
        ws = ws_manager.get_target_ws(uid)
        ws_manager.disconnect(uid,ws)
    return {"msg":"已下线"}
