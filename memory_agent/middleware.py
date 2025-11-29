import logging
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage

from memory_tools import recall_memory
from tools.graph_tools import query_graph

# Configure logging
logger = logging.getLogger(__name__)


class MemoryMiddleware:
    """
    Middleware to automatically retrieve and inject context from memory
    before the agent processes a message.
    """

    def __init__(self):
        pass

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Simple keyword extraction. In a real system, use an LLM or NLP library.
        For now, we'll just use the text itself as the query if it's short,
        or extract capitalized words (potential entities).
        """
        # Very naive implementation for MVP
        import string

        words = text.split()
        keywords = []
        for w in words:
            # Strip punctuation
            clean_w = w.strip(string.punctuation)
            if clean_w and clean_w[0].isupper() and clean_w.isalpha():
                keywords.append(clean_w)

        if not keywords:
            return [text[:50]]  # Fallback to first 50 chars
        return keywords

    def retrieve_context(self, message: str) -> str:
        """
        Queries Weaviate and Neo4j for context relevant to the message.
        """
        context_parts = []

        # 1. Semantic Search (Weaviate)
        # We use the whole message for BM25/Vector search usually
        semantic_context = recall_memory.invoke(message)
        if semantic_context and "No relevant memories found" not in semantic_context:
            context_parts.append(f"--- Semantic Memory ---\n{semantic_context}")

        # 2. Graph Search (Neo4j)
        # Extract entities to query the graph
        keywords = self._extract_keywords(message)
        for kw in keywords:
            # Look for nodes with this name
            cypher = f"MATCH (n {{name: '{kw}'}}) RETURN n"
            graph_result = query_graph.invoke(cypher)
            if graph_result and "No results found" not in graph_result:
                context_parts.append(f"--- Knowledge Graph ({kw}) ---\n{graph_result}")

                # Also look for immediate relationships
                cypher_rel = (
                    f"MATCH (n {{name: '{kw}'}})-[r]-(m) RETURN n.name, type(r), m.name"
                )
                rel_result = query_graph.invoke(cypher_rel)
                if rel_result and "No results found" not in rel_result:
                    context_parts.append(f"--- Relationships ({kw}) ---\n{rel_result}")

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    def process_input(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Inspects the last user message, retrieves context, and injects it
        as a SystemMessage or appends it to the UserMessage.
        """
        if not messages:
            return messages

        last_msg = messages[-1]
        if isinstance(last_msg, HumanMessage):
            content = last_msg.content
            if isinstance(content, list):
                content = str(content)
            context = self.retrieve_context(content)
            if context:
                print(f"\n[MemoryMiddleware] Auto-retrieved context:\n{context}\n")
                # Inject as a System Message right before the Human Message
                # Or modify the Human Message. Modifying Human Message is often safer for some models.
                # Let's append to the Human Message for clarity in this ReAct loop.
                new_content = f"{last_msg.content}\n\n[SYSTEM: The following context was automatically retrieved from your memory]\n{context}"
                messages[-1] = HumanMessage(content=new_content)

        return messages
