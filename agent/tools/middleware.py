from typing import Callable
from langchain.agents import AgentState
from langchain.agents.middleware import before_model,dynamic_prompt,wrap_tool_call,ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
from utils.prompt_loader import load_report_prompts,load_system_prompts

@wrap_tool_call
def monitor_tool(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command]

)-> ToolMessage | Command:
    """工具房门口的门卫：登记每次工具调用 + 盯信号弹"""
    logger.info(f"[Tool monitor]执行工具: {request.tool_call['name']}")
    logger.info(f"[Tool monitor]工具输入: {request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[Tool monitor]工具: {request.tool_call['name']} 执行结果: {result}")

        # 信号弹检测:
        if request.tool_call["name"] == 'fill_context_for_report':
            request.runtime.context["report"] = True
            logger.info("[Tool monitor]信号弹检测: 发现报告生成任务，已设置信号弹")

        return result
    except Exception as e:
        logger.error(f"[Tool monitor]工具: {request.tool_call['name']} 执行出错,原因: {str(e)}")
        raise e

@before_model
def log_before_model(
        state: AgentState,
        runtime: Runtime,
):
    """在模型生成之前记录日志"""
    logger.info(f"[log_before_model]模型即将调用: 带有{len(state['messages'])}条消息")
    logger.debug(
        f"[log_before_model]模型输入: {type(state['messages'][-1]).__name__}:"
        f"{state['messages'][-1].content.strip()}"
    )
    return None

@dynamic_prompt
def report_prom_switch(request: ModelRequest) -> str:
    """换装间门口的门卫：每次发提示词前查记事板，决定穿哪件制服"""
    is_report = request.runtime.context.get("report", False)
    if is_report:
        logger.info("[report_prom_switch]检测到报告模式标记，切换到报告写手提示词")
        return load_report_prompts()
    return load_system_prompts()



