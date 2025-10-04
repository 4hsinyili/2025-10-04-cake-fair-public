from google.adk.agents import LlmAgent

from app.core import load_open_router_model

str_agent = LlmAgent(
    name="str_agent",
    model=load_open_router_model(),
    instruction="extract string from user input, and store it to state['str_value']",
    description="root agent for response preference assistant",
    output_key="str_value",
)

int_agent = LlmAgent(
    name="int_agent",
    model=load_open_router_model(),
    instruction="extract integer from user input, and store it to state['int_value']",
    description="root agent for response preference assistant",
    output_key="int_value",
)


root_agent = LlmAgent(
    name="root_agent",
    model=load_open_router_model(),
    instruction="Please call str_agent and int_agent to extract values from user input, and the values from state['str_value'] and state['int_value'], then return the final result in format `<str_value>_<int_value>`.",
    description="root agent",
    sub_agents=[str_agent, int_agent],
)
