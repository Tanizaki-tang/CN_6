@app.post("/register")
async def register(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    #Form:网页form表单
    #Depends：依赖注入，实现自动管理生成器生命周期
    username = username.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    exist = db.query(DBUser).filter(DBUser.username == username).first()
    if exist: raise HTTPException(status_code=400, detail="用户名已存在")
    new_user = DBUser(username=username, hashed_pw=hash_password(password))
    db.add(new_user)
    db.commit()
    return {"msg":"注册成功"}

# 登录
@app.post("/login")
async def login(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.username == username.strip()).first()
    if not user or not verify_password(password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="账号密码错误")
    # 这里不置 is_online：真正上线以 WebSocket 建连为准，
    # 否则用户只登录不连 WS 会永远显示在线
    return {"uid": user.id, "name":user.username}

# 登出
@app.post("/logout/{uid}")
async def logout(uid:int, db:Session=Depends(get_db)):
    user = db.get(DBUser, uid)
    if user:
        user.is_online = False
        db.commit()
        ws_manager.disconnect(uid)
        await ws_manager.broadcast_online(db)
    return {"msg":"已下线"}