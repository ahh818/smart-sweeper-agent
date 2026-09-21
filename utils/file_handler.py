import hashlib
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from utils.logger_handler import logger
from utils.path_tool import get_abs_path


def get_file_md5_hex(filepath: str) -> str | None:
    """计算文件的 md5 十六进制字符串（文件'指纹'）"""
    if not os.path.exists(filepath):
        logger.error(f"{filepath} 文件不存在")
        return None
    if not os.path.isfile(filepath):
        logger.error(f"{filepath} 不是文件")
        return None

    md5_obj = hashlib.md5()
    chunk_size = 8192
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)

                if not chunk:
                    break

                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    
    except Exception as e:
        logger.error(f"计算文件 {filepath} 的 md5 出错: {str(e)}")
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> tuple[str, ...]:
    """返回文件夹内，以 allowed_types 中任一项结尾的文件的完整路径"""
    files = []
    if not os.path.isdir(path):
        logger.error(f"[listdir_with_allowed_type] {path} 不是文件夹")
        return ()

    for file in os.listdir(path):
        if file.endswith(allowed_types):
            files.append(os.path.join(path, file))
    return tuple(files)


def pdf_loader(filepath: str, password=None) -> list[Document]:
    return PyPDFLoader(filepath, password).load()


def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath, encoding="utf-8").load()


if __name__ == '__main__':
    # 1. 算指纹
    md5 = get_file_md5_hex(get_abs_path("data/故障排除.txt"))
    print("文件指纹:", md5)

    # 2. 找文件
    files = listdir_with_allowed_type(get_abs_path("data"), ("txt", "pdf"))
    print("发现知识文件:", len(files), "个")
    for f in files:
        print(" -", os.path.basename(f))

    # 3. 读成 Document
    docs = txt_loader(get_abs_path("data/故障排除.txt"))
    print("加载到文档块数:", len(docs))
    print("第一块的货单(metadata):", docs[0].metadata)
    print("第一块内容开头:", docs[0].page_content[:60])