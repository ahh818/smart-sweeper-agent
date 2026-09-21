from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompt
from utils.logger_handler import logger


class RagSummarizeService(object):
    """RAG 总结服务：检索资料 → 拼提示词 → 让模型总结"""

    def __init__(self):
        self.vector_store = VectorStoreService()                          # ① 向量库服务
        self.retriever = self.vector_store.get_retriever()                # ② 检索器
        self.prompt_text = load_rag_prompt()                              # ③ 提示词文本
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)  # ④ 模板对象
        self.model = chat_model                                           # ⑤ 模型
        self.chain = self._init_chain()                                   # ⑥ 链（流水线）

    def _init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query: str) -> list[Document]:
        """检索最相关的文档块"""
        result = self.retriever.invoke(query)
        logger.debug("============ RAG 检索 ============")
        logger.debug(f"问题：{query}")
        logger.debug(f"命中：{len(result)} 条")
        for i, doc in enumerate(result):
            logger.debug(f"--- 第 {i + 1} 条 ---")
            logger.debug(doc.page_content)
            logger.debug(f"来源：{doc.metadata}")
        return result

    def rag_summarize(self, query: str) -> str:
        """RAG 总结：检索 → 拼上下文 → 模型总结"""
        # 第 1 步：找——把最相关的资料捞出来
        context_docs = self.retriever_docs(query)

        # 第 2 步：拼——把资料们缝成一段"上下文"文本
        context = ""
        for i, doc in enumerate(context_docs):
            context += f"【参考资料{i + 1}】{doc.page_content}\n"

        # 第 3 步：说——交给链：填提示词 → 模型总结
        answer = self.chain.invoke({
            "input": query,
            "context": context,
        })
        return answer

if __name__ == '__main__':
        rag = RagSummarizeService()
        answer = rag.rag_summarize("扫地机器人怎么选购")
        print("============ 最终回答 ============")
        print(answer)