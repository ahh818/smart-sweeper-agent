from utils.config_handler import prompts_conf
from utils.path_tool import get_abs_path


def load_rag_prompt() -> str:
    """读取 RAG 总结提示词文件，返回全文字符串"""
    rag_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    with open(rag_prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def load_system_prompts() -> str:
    """读取 Agent 系统提示词"""
    system_prompt_path = get_abs_path(prompts_conf["main_prompt_path"])
    with open(system_prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def load_report_prompts() -> str:
    """读取报告写手提示词"""
    report_prompt_path = get_abs_path(prompts_conf["report_prompt_path"])
    with open(report_prompt_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == '__main__':
    print(load_system_prompts()[:60])
    print("---")
    print(load_report_prompts()[:60])
    print("---")
    print(load_rag_prompt()[:60])