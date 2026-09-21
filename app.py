import streamlit as st
from agent.react_agent import ReactAgent

st.title("智扫通机器人智能客服")
st.divider()

#第一次访问时初始化,重跑时保留
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

#把储物柜里的历史消息重新绘制到页面
for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入框（页面底部）
prompt = st.chat_input("用户输入")

if prompt:
    # 1. 画出用户这条消息的气泡
    st.chat_message("user").write(prompt)

    # 2. 存进储物柜的历史记录
    st.session_state["messages"].append({
        "role": "user",
        "content": prompt
    })

    response_messages = []

    with st.spinner("智能客服思考中..."):

        # 传整段会话（末尾已是用户本次提问），让 Agent 能看到前文
        res_stream = st.session_state["agent"].execute_stream(st.session_state["messages"])

        def capture(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                yield chunk


        st.chat_message("assistant").write_stream(
            capture(res_stream, response_messages)
        )


    full_response = "".join(response_messages)

    st.session_state["messages"].append({
        "role": "assistant",
        "content": full_response
    })

    st.rerun()



