import operator
from typing import Annotated, List, TypedDict
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import create_react_agent

from tools.research_tools import get_research_tools
from tools.code_tools import get_code_tools
from tools.file_tools import get_file_tools
from tools.git_tools import get_git_tools
from tools.meta_tools import get_meta_tools
from tools.infra_tools import get_infra_tools
from tools.graph_tools import get_graph_tools
from memory_tools import save_memory, recall_memory


# Define the state of the team
class TeamState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next_agent: str


def get_llm():
    model_name = os.environ.get("MiniMax_M2_MODEL", "minimax-m2")
    base_url = os.environ.get("MiniMax_M2_BASE_URL", "https://api.minimax.io/anthropic")
    return ChatAnthropic(model=model_name, temperature=0.7, base_url=base_url)


def create_planner_agent(llm):
    tools = (
        get_research_tools()
        + get_file_tools()
        + [save_memory, recall_memory]
        + get_graph_tools()
    )
    prompt = (
        "You are the Planner Agent. Your job is to break down complex user requests into "
        "detailed, step-by-step technical implementation plans. "
        "Use research tools to verify assumptions if needed. "
        "You have access to 'Deep Memory': "
        "1. Semantic Memory (save_memory/recall_memory) for facts and context. "
        "2. Knowledge Graph (add_graph_node/add_graph_edge/query_graph) for mapping relationships (e.g. dependencies, architecture). "
        "Always check the Knowledge Graph for existing context before starting a new plan. "
        "Output a clear plan that the Coder Agent can follow."
    )
    return create_react_agent(llm, tools, prompt=prompt)


def create_coder_agent(llm):
    tools = (
        get_code_tools()
        + get_file_tools()
        + get_git_tools()
        + get_meta_tools()
        + get_infra_tools()
    )
    prompt = (
        "You are the Coder Agent. Your job is to implement code based on the plan provided. "
        "You have full access to the file system, code execution, and git. "
        "Write clean, efficient, and documented code. "
        "After implementing, verify your work."
    )
    return create_react_agent(llm, tools, prompt=prompt)


def create_reviewer_agent(llm):
    tools = (
        get_file_tools() + get_code_tools() + get_graph_tools()
    )  # Needs to read files and maybe run tests
    prompt = (
        "You are the Reviewer Agent. Your job is to review the code written by the Coder Agent. "
        "Check for bugs, security vulnerabilities, and adherence to the plan. "
        "Verify that the architecture matches the Knowledge Graph definitions if applicable. "
        "If you find issues, provide specific feedback to the Coder. "
        "If everything looks good, approve the changes."
    )
    return create_react_agent(llm, tools, prompt=prompt)


def build_team_graph(checkpointer=None):
    llm = get_llm()

    planner = create_planner_agent(llm)
    coder = create_coder_agent(llm)
    reviewer = create_reviewer_agent(llm)

    # Define nodes
    def planner_node(state: TeamState):
        result = planner.invoke(state)
        return {"messages": [result["messages"][-1]]}

    def coder_node(state: TeamState):
        result = coder.invoke(state)
        return {"messages": [result["messages"][-1]]}

    def reviewer_node(state: TeamState):
        result = reviewer.invoke(state)
        return {"messages": [result["messages"][-1]]}

    def supervisor_node(state: TeamState):
        messages = state["messages"]
        last_message = messages[-1]

        # Simple heuristic-based routing for this MVP
        # In a real system, we'd use function calling or structured output to choose the next agent
        content = last_message.content
        if isinstance(content, list):
            text_content = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
            content = text_content.lower()
        elif isinstance(content, str):
            content = content.lower()
        else:
            content = ""

        print(f"[Supervisor] Analyzing content: {content[:100]}...")

        if (
            "plan" in content
            and "approved" not in content
            and "implement" not in content
        ):
            print("[Supervisor] Routing to Coder")
            return {"next_agent": "Coder"}
        elif "implemented" in content or "code" in content:
            print("[Supervisor] Routing to Reviewer")
            return {"next_agent": "Reviewer"}
        elif "issue" in content or "bug" in content:
            print("[Supervisor] Routing to Coder")
            return {"next_agent": "Coder"}
        elif "approved" in content or "finish" in content:
            print("[Supervisor] Routing to FINISH")
            return {"next_agent": "FINISH"}
        else:
            # If it's a user message, start with Planner
            if isinstance(last_message, HumanMessage):
                print("[Supervisor] User message -> Routing to Planner")
                return {"next_agent": "Planner"}
            # If it's an agent message and no other condition met, return to user
            print("[Supervisor] No condition met -> Routing to FINISH")
            return {"next_agent": "FINISH"}

    workflow = StateGraph(TeamState)

    workflow.add_node("Planner", planner_node)
    workflow.add_node("Coder", coder_node)
    workflow.add_node("Reviewer", reviewer_node)
    workflow.add_node("Supervisor", supervisor_node)

    # Edges
    workflow.add_edge(START, "Supervisor")

    workflow.add_conditional_edges(
        "Supervisor",
        lambda x: x["next_agent"],
        {"Planner": "Planner", "Coder": "Coder", "Reviewer": "Reviewer", "FINISH": END},
    )

    workflow.add_edge("Planner", "Supervisor")
    workflow.add_edge("Coder", "Supervisor")
    workflow.add_edge("Reviewer", "Supervisor")

    return workflow.compile(checkpointer=checkpointer)
