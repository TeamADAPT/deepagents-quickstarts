import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def expand_vars(text):
    """Expands shell-style variables with defaults."""
    import re

    pattern = re.compile(r"\$\{([^}:]+)(?::-([^}]+))?\}")

    def replace(match):
        key = match.group(1)
        default = match.group(2)
        return os.environ.get(key, default if default is not None else "")

    return pattern.sub(replace, text)


def load_secrets():
    """Loads secrets from env files."""
    secrets_files = ["/adapt/secrets/m2.env", "/adapt/secrets/db.env"]
    for path in secrets_files:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]
                        if key not in os.environ:
                            os.environ[key] = value

    for key, value in os.environ.items():
        if "${" in value:
            os.environ[key] = expand_vars(value)


def get_postgres_connection_string():
    db_url = os.environ.get("POSTGRES_CLUSTER_URLS")
    if not db_url:
        raise ValueError("POSTGRES_CLUSTER_URLS not found")
    db_url = expand_vars(db_url)
    if "," in db_url:
        db_url = db_url.split(",")[0].strip()
    return db_url


def inspect_checkpoints():
    load_secrets()
    conn_string = get_postgres_connection_string()

    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()

        # Check for checkpoints table
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tables found: {tables}")

        if "checkpoints" in tables:
            print("\nQuerying unique thread_ids from checkpoints:")
            cur.execute("SELECT DISTINCT thread_id FROM checkpoints")
            thread_ids = [row[0] for row in cur.fetchall()]
            for tid in thread_ids:
                print(f" - {tid}")

            if "default_thread_v2" in thread_ids:
                print("\nSUCCESS: Found 'default_thread_v2' in database!")
            else:
                print("\nWARNING: 'default_thread_v2' NOT found in database.")
        else:
            print("No 'checkpoints' table found.")

        conn.close()

    except Exception as e:
        print(f"Error connecting to DB: {e}")


if __name__ == "__main__":
    inspect_checkpoints()
