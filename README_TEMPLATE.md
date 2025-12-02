# Nova Agent Template

This is the standard template for building "Nova" agents within the DeepAgents framework. It comes pre-configured with a full stack of memory and observability tools.

## Features

*   **Full Stack Memory**:
    *   **Redis (DragonflyDB)**: Caching for LLM responses (Port 18000).
    *   **PostgreSQL**: Durable state checkpointing (Port 18030).
    *   **MongoDB**: Document store for large unstructured data (Port 18070).
*   **Episodic Memory**: Automatic reflection and summarization of conversations.
*   **Semantic & Graph Memory**: Integration with Weaviate and Neo4j.
*   **Observability**: Built-in LangSmith tracing.

## How to Use

1.  **Copy the Template**:
    ```bash
    cp template_agent.py my_new_agent.py
    ```

2.  **Define Your Team**:
    *   The template imports `build_team_graph` from `team_structure.py`.
    *   You should create a new team structure file (e.g., `my_team.py`) or modify the existing one to define your agents and workflow.
    *   Update the import in `my_new_agent.py`:
        ```python
        from my_team import build_team_graph
        ```

3.  **Run Your Agent**:
    ```bash
    python3 my_new_agent.py
    ```

## Configuration

The agent automatically loads secrets from:
*   `/adapt/secrets/m2.env`
*   `/adapt/secrets/db.env`

Ensure these files are present and contain the necessary API keys (MiniMax/Anthropic) and database URLs.

## Directory Structure

*   `template_agent.py`: The runner/harness.
*   `team_structure.py`: The logic (Graph definition).
*   `memory_tools.py`: Weaviate integration.
*   `tools/`: Directory for agent tools.
*   `cache_tools.py`: Redis setup.
*   `reflection.py`: Episodic memory logic.
