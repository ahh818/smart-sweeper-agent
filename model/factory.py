import os
from abc import abstractmethod, ABC
from typing import Optional
from langchain.embeddings import Embeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from utils.config_handler import rag_conf
from utils.path_tool import get_abs_path
from dotenv import load_dotenv



load_dotenv(get_abs_path(".env"))

class BaseModelFactory(ABC):
    """模型工厂的合同:所有工厂都必须提供 generator 方法"""
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass

class ChatModelFactory(BaseModelFactory):
    """聊天模型工厂"""
    def generator(self) -> Optional[Embeddings |BaseChatModel]:
        return ChatOpenAI(
            model_name=rag_conf["chat_model_name"],
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

class EmbeddingsFactory(BaseModelFactory)  :
    """生产"把文字变向量"的模型"""

    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(
            model=rag_conf["embedding_model_name"],
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        )

# 开工厂 → 让工厂生产出模型对象（模块被 import 时就绪）
chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()


if __name__ == '__main__':
    print("chat 模型：", type(chat_model))
    res = chat_model.invoke("你好，用一句话介绍你自己")
    print("模型回复：", res.content)

    print("embedding 模型：", type(embed_model))
    vec = embed_model.embed_query("清扫后地面还有灰尘")
    print("向量维度：", len(vec))
    print("向量前5位：", vec[:5])