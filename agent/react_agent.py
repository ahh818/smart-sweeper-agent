from langchain.agents import create_agent

from agent.tools.agent_tools import (fetch_external_data, fill_context_for_report,
                                     get_current_month, get_user_id,
                                     get_user_location, get_weather, rag_summarize)
from agent.tools.middleware import trim_history,log_before_model, monitor_tool, report_prom_switch
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
                fetch_external_data,
                get_current_month,
                get_user_id,
                get_user_location,
                get_weather,
                rag_summarize,
                fill_context_for_report
            ],
            middleware=[trim_history,log_before_model, monitor_tool, report_prom_switch]
        )

    def execute_stream(self, messages: list[dict]):
        """messages 为整段会话（含用户本次提问），形如 [{"role": "user", "content": "..."}, ...]"""
        input_dict = {"messages": list(messages)}
        for chunk, metadata in self.agent.stream(
                input_dict,
                stream_mode="messages",
                context={"report": False}
        ):
            if chunk.content:
                yield chunk.content


if __name__ == '__main__':
    agent = ReactAgent()
    dialog = [{"role": "user", "content": "清扫后地面还有灰尘、碎屑"}]
    for chunk in agent.execute_stream(dialog):
        print(chunk, end="", flush=True)
