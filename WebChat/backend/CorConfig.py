"""
FastAPI 的 CORSMiddleware 中间件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setupCors(app : FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins =["http://localhost:8080", "http://127.0.0.1:8080"],
        allow_credentials=True,
        allow_methods=["GET","HEAD","POST","PUT","DELETE","OPTIONS"],
        allow_headers=["*"],
        max_age=3600 #300s=1h，控制浏览器缓存OPTIONS预检请求结果的时间
    )

