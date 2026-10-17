from pydantic import BaseModel,model_validator,ValidationError
from typing import List,Optional,Literal

class OnlineUser(BaseModel):
    """在线用户：前端必须拿到 uid 才能指定私聊的 target_uid"""
    uid:int
    name:str

class UserList(BaseModel):
    #保留 userlist(纯名字)兼容旧前端；users 里额外带 uid
    userlist: List[str]
    users: List[OnlineUser] = []

class GroupInfo(BaseModel):
    """群信息：前端靠 is_member / member_count 决定显示"进入"还是"加入" """
    group_id:int
    group_name:str
    owner_id:Optional[int] = None   #没有 owner 的旧数据
    member_count:int = 0
    is_member:bool = False

class Message(BaseModel):
    msg_type: Literal['private','group']
    time:str
    content:str = ""          #纯图片消息可以只传 img_url
    img_url : Optional[str] =None
    target_uid:Optional[int]=None
    group_id:Optional[int] =None

    @model_validator(mode='after')
    def check_rules(self):
        # content、img_url至少一个存在
        if not self.content and not self.img_url:
            raise ValueError("content和img_url不能同时为空")
        # private消息必须带target_uid
        if self.msg_type == "private" and self.target_uid is None:
            raise ValueError("私聊消息需要target_uid")
        # group消息必须带group_id
        if self.msg_type == "group" and self.group_id is None:
            raise ValueError("群聊消息需要group_id")
        return self