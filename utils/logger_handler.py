import logging
import os
from datetime import datetime
from utils.path_tool import get_abs_path


# 准备日志文件夹
LOG_ROOT=get_abs_path("logs")
os.makedirs(LOG_ROOT,exist_ok=True)

# 默认的日志格式
DEFAULT_LOGGING_FORMAT = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_logger(
        name: str = "agent",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        log_file=None,
) -> logging.Logger:
    """
    获取logger
    :param name: 日志名称
    :param console_level: 控制台日志级别
    :param file_level: 文件日志级别
    :param log_file: 日志文件名
    :return: logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复日志
    if logger.handlers:
        return logger
    # Handler 一：控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOGGING_FORMAT)
    logger.addHandler(console_handler)

    # Handler 二：文件（默认按"名字_日期"命名）
    if not log_file:
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y-%m-%d')}")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOGGING_FORMAT)
    logger.addHandler(file_handler)

    return logger

# 全局日志器：别的模块 from utils.logger_handler import logger 直接用
logger = get_logger()

if __name__ == '__main__':

    logger.debug("调试日志：开发时看的细节")
    logger.info("信息日志：正常流程记录")
    logger.warning("警告日志：有隐患但不致命")
    logger.error("错误日志：出问题了")