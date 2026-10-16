ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# 图片上传
@app.post("/upload_img")
async def upload_img(file:UploadFile=File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMG_EXT:
        raise HTTPException(status_code=400, detail="只支持 png/jpg/jpeg/gif/webp/bmp 图片")
    save_dir = "static/uploads"
    os.makedirs(save_dir, exist_ok=True)
    # 用随机名，避免路径穿越(../../)和同名文件互相覆盖
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(save_dir, filename), "wb") as f:
        shutil.copyfileobj(file.file, f)
    await file.close()
    return {"img_url": f"/static/uploads/{filename}"}

# 获取历史消息
@app.get("/history")
async def get_history(uid:int, target_uid:int=None, group_id:int=None, db:Session=Depends(get_db)):
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