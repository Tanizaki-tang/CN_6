import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),    #输出到控制台
        logging.FileHandler("app.log", encoding="utf-8"),   #输出到文件
    ],
)

def get_logger(name:str)-> logging.Logger:
    """根据传入的name创建日志器"""
    return logging.getLogger(name)