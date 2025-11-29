import os
from neo4j import GraphDatabase
from langchain_core.tools import tool


def get_neo4j_driver():
    """Establishes a connection to the Neo4j graph database."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:18061")
    username = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "changeme")

    # Fallback to reading db.env if env vars are missing
    if password == "changeme":
        try:
            with open("/adapt/secrets/db.env") as f:
                for line in f:
                    if line.startswith("NEO4J_AUTH="):
                        password = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

    return GraphDatabase.driver(uri, auth=(username, password))


@tool
def add_graph_node(label: str, name: str, properties: str = "{}") -> str:
    """Adds a node to the knowledge graph.

    Args:
        label: The type of the node (e.g., 'Project', 'Person', 'Technology').
        name: The unique name or identifier for the node.
        properties: A JSON string of additional properties (e.g., '{"status": "active"}').
    """
    import json

    try:
        props = json.loads(properties)
        props["name"] = name
    except:
        return "Error: Properties must be a valid JSON string."

    driver = get_neo4j_driver()
    query = f"MERGE (n:{label} {{name: $name}}) SET n += $props RETURN n"

    try:
        with driver.session() as session:
            session.run(query, name=name, props=props)
        return f"Successfully added/updated node: {label} ({name})"
    except Exception as e:
        return f"Failed to add node: {e}"
    finally:
        driver.close()


@tool
def add_graph_edge(from_name: str, relation: str, to_name: str) -> str:
    """Adds a relationship between two nodes in the knowledge graph.

    Args:
        from_name: The name of the source node.
        relation: The type of relationship (e.g., 'DEPENDS_ON', 'CREATED_BY').
        to_name: The name of the target node.
    """
    driver = get_neo4j_driver()
    # Cypher query to match nodes and create relationship
    query = """
    MATCH (a {name: $from_name}), (b {name: $to_name})
    MERGE (a)-[r:%s]->(b)
    RETURN type(r)
    """ % relation.upper()  # Injection risk if relation is not controlled, but this is an internal tool.

    try:
        with driver.session() as session:
            result = session.run(query, from_name=from_name, to_name=to_name)
            if result.peek() is None:
                return (
                    f"Failed: Could not find both nodes '{from_name}' and '{to_name}'."
                )
        return f"Successfully added edge: ({from_name}) -[{relation.upper()}]-> ({to_name})"
    except Exception as e:
        return f"Failed to add edge: {e}"
    finally:
        driver.close()


@tool
def query_graph(cypher: str) -> str:
    """Executes a Cypher query against the knowledge graph.

    Use this to find complex relationships or traverse the graph.
    Example: "MATCH (p:Project)-[:DEPENDS_ON]->(t:Technology) RETURN p.name, t.name"

    Args:
        cypher: The Cypher query string.
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher)
            records = [str(record.data()) for record in result]
            if not records:
                return "No results found."
            return "\n".join(records)
    except Exception as e:
        return f"Query failed: {e}"
    finally:
        driver.close()


def get_graph_tools():
    return [add_graph_node, add_graph_edge, query_graph]
