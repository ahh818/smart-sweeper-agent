from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.file_handler import (get_file_md5_hex, listdir_with_allowed_type,
                                pdf_loader, txt_loader)
from utils.logger_handler import logger
import os
from model.factory import embed_model
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path


class VectorStoreService:
    """向量库服务：知识文件的入库与检索入口"""

    def __init__(self):
        # 打开（不存在则创建）向量库
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        )

        # 文字切块器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def load_documents(self):
        """ 扫描 data/ 目录，把没入过库的知识文件：读取 → 切块 → 向量化入库"""

        def check_md5_hex(md5_for_hex: str) -> bool:
            md5_store_path = get_abs_path(chroma_conf["md5_hex_store"])
            if not os.path.exists(md5_store_path):
                open(md5_store_path, "w", encoding="utf-8").close()
                return  False
            with open(md5_store_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip() == md5_for_hex:
                        return True
            return False

        def save_md5_hex(md5_for_hex: str) :
            """把新指纹记进账本（a = append 追加模式）"""
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_hex + "\n")

        def get_file_documents(read_path: str) :
            #按后缀选择合适的读取器
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            elif read_path.endswith("pdf"):
                return pdf_loader(read_path)
            else:
                raise ValueError(f"文件类型: {read_path} 不支持")
        # 主流程上半——找文件 + 查账 + 跳过
        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]), ("txt", "pdf")
        )
        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex):
                logger.info(f"加载数据库文件{path}已存在，跳过加载")
                continue
        #主流程下半——干活 + 记账 + 保护
            try:
                documents = get_file_documents(path)
                if not documents:
                    logger.info(f"[加载知识库]: {path} 内没有有效文本内容，跳过加载")
                    continue
                split_documents = self.spliter.split_documents(documents)

                if not split_documents:
                    logger.info(f"[加载知识库]: {path} 切块后没有有效文本内容，跳过加载")
                    continue
                self.vector_store.add_documents(split_documents)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]: {path} 成功")
            except Exception as e:
                logger.error(f"[加载知识库]: {path} 出现错误，跳过加载")
                logger.error(e)

    def get_retriever(self):
        """返回检索器：喂一个问题，返回最相关的文档块"""
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})


if __name__ == '__main__':

        vs = VectorStoreService()
        vs.load_documents()  # 第二次运行：应该全部"跳过加载"

        retriever = vs.get_retriever()
        results = retriever.invoke("清扫后地面还有灰尘、碎屑")
        print("检索到:", len(results), "条")
        for i, doc in enumerate(results):
            print(f"===== 第 {i + 1} 条 =====")
            print(doc.page_content[:120])
            print("来源:", doc.metadata.get("source"))