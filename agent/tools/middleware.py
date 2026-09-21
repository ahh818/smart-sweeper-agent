from typing import Callable
from langchain.agents import AgentState
from langchain.agents.middleware import before_model,dynamic_prompt,wrap_tool_call,ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import RemoveMessage,ToolMessage
from utils.config_handler import agent_conf
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
from utils.prompt_loader import load_report_prompts, load_system_prompts, load_thinking_rule

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
        prompt = load_report_prompts()
    else:
        prompt = load_system_prompts()

    # 思考过程输出开关：与业务模式正交的运行时维度
    if agent_conf["show_thinking"]:
        prompt += "\n\n" + load_thinking_rule()

    return prompt

@before_model
def trim_history(state: AgentState, runtime: Runtime):
    """上下文裁剪：消息数超过上限时，移除最早的部分"""
    messages = state["messages"]
    limit = agent_conf["max_history_messages"]
    if len(messages) <= limit:
        return None

    keep_from = len(messages) - limit
    # 不能以 ToolMessage 开头——它的 AIMessage 父消息已被裁掉，孤儿 ToolMessage 会让 API 报错
    while keep_from < len(messages) and isinstance(messages[keep_from], ToolMessage):
        keep_from += 1

    to_remove = messages[:keep_from]
    logger.info(f"[trim_history]消息 {len(messages)} 条超过上限 {limit}，裁剪最早 {len(to_remove)} 条")
    return {"messages": [RemoveMessage(id=m.id) for m in to_remove]}

