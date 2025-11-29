from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from team_structure import get_llm
from memory_tools import save_memory
from tools.graph_tools import add_graph_node, add_graph_edge
import json


def reflect_on_conversation(state):
    """
    Analyzes the conversation history to extract episodic memories and knowledge graph updates.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    # Extract text content from messages
    conversation_text = ""
    for msg in messages[-10:]:  # Analyze last 10 messages to keep it focused
        role = "User" if isinstance(msg, HumanMessage) else "Agent"
        content = msg.content
        if isinstance(content, list):
            content = " ".join(
                [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
            )
        conversation_text += f"{role}: {content}\n"

    llm = get_llm()

    # Prompt for reflection
    prompt = ChatPromptTemplate.from_template("""
    You are the "Subconscious Memory" of an AI agent. 
    Analyze the following conversation snippet and extract:
    1. A concise summary of what was achieved or discussed (for Semantic Memory).
    2. Key entities (Projects, Tools, Concepts) and their types (for Knowledge Graph).
    3. Relationships between these entities (for Knowledge Graph).

    Conversation:
    {conversation}

    Output JSON format:
    {{
        "summary": "...",
        "entities": [{{"name": "...", "type": "..."}}],
        "relationships": [{{"from": "...", "to": "...", "type": "..."}}]
    }}
    """)

    chain = prompt | llm

    try:
        response = chain.invoke({"conversation": conversation_text})
        content = response.content

        # Handle list content (MiniMax/Anthropic sometimes returns list of blocks)
        if isinstance(content, list):
            text_content = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
            content = text_content

        # Parse JSON (handle potential markdown wrapping)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        # 1. Save Summary to Semantic Memory
        summary = data.get("summary")
        if summary:
            print(f"[Reflection] Saving summary: {summary}")
            save_memory.invoke({"content": summary})

        # 2. Update Knowledge Graph
        for entity in data.get("entities", []):
            print(f"[Reflection] Adding node: {entity}")
            # Map to correct tool arguments: name, label, properties
            add_graph_node.invoke(
                {"name": entity["name"], "label": entity["type"], "properties": "{}"}
            )

        for rel in data.get("relationships", []):
            print(f"[Reflection] Adding edge: {rel}")
            # Map to correct tool arguments: from_node, to_node, relation_type
            add_graph_edge.invoke(
                {
                    "from_node": rel["from"],
                    "to_node": rel["to"],
                    "relation_type": rel["type"],
                }
            )

        return {
            "messages": [SystemMessage(content=f"[System] Episodic memory updated.")]
        }

    except Exception as e:
        print(f"[Reflection] Error: {e}")
        return {}
