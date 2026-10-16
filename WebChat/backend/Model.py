from pydantic import BaseModel,model_validator,ValidationError
from typing import List,Optional,Literal

class UserList(BaseModel):
    userlist: List[str]

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