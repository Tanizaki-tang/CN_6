from pydantic import BaseModel
from typing import List

class UserList(BaseModel):
    userlist: List[str]

class Message(BaseModel):
    name: str
    time:str
    msg:str
    #image :待实现