from sqlalchemy.orm import sessionmaker,Session,DeclarativeBase
from sqlalchemy import create_engine,Column,Integer,String, Boolean , DateTime, ForeignKey

DB_URL ="sqlite:///./chat.db"
engine= create_engine(DB_URL,connect_args={"check_same_thread":False})
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

import datetime
def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)    #去掉了时区信息

#region 数据库模型

#数据库模型，注意与普通python类的写法不同
class DBUser(DeclarativeBase):
    __tablename__ = "users"
    id = Column(Integer , primary_key=True, index=True)
    username = Column(String, unique=True)
    hashed_pw = Column(String)
    is_online = Column(Boolean,default=False)

class DBMessage(DeclarativeBase):
    __tablename__="messages"
    id=Column(Integer,primary_key=True)
    sender_id=Column(Integer,ForeignKey('users.id'))
    receiver_id = Column(Integer,nullable= True)    #私聊用户id
    group_id= Column(Integer,nullable=True) #群聊
    content = Column(String,nullable=True)
    img_url = Column(String, nullable=True) #可选的发图功能
    create_time = Column(DateTime,default=utc_now)

class DBGroup(DeclarativeBase):
    __tablename__="groups"
    id = Column(Integer,primary_key=True)
    group_name=Column(String)

#endregion

def get_db():
    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()
