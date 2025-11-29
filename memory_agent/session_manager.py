import os
import hashlib
import uuid
import json
from tools.dragonfly_tools import get_redis_client


class SessionManager:
    def __init__(self):
        self.project_id = self._get_project_id()
        self.agent_id = os.environ.get("AGENT_ID", "default-agent")
        self.cwd = os.getcwd()
        self.session_id = self._generate_session_id()
        self.redis = get_redis_client()

        # Ensure session is registered
        self._register_session()

    def _get_project_id(self):
        # Try to find a project ID from env or path
        # For now, generate one based on the directory path hash if not set
        if "PROJECT_ID" in os.environ:
            return os.environ["PROJECT_ID"]

        # Hash the current directory to get a stable ID for this workspace
        cwd_hash = hashlib.md5(os.getcwd().encode()).hexdigest()[:8]
        return f"proj-{cwd_hash}"

    def _generate_session_id(self):
        if "SESSION_ID" in os.environ:
            return os.environ["SESSION_ID"]

        # Session ID combines Project, Agent, and CWD to allow concurrent agents
        # in different dirs to have different sessions.
        # We also add a random component if we want unique sessions per run,
        # but the user asked for "history remember that" per dir.
        # So let's make it stable per directory/agent combo.
        unique_str = f"{self.project_id}-{self.agent_id}-{self.cwd}-{uuid.uuid4()}"  # Force unique for now
        sess_hash = hashlib.md5(unique_str.encode()).hexdigest()[:12]
        return f"sess-{sess_hash}"

    def _register_session(self):
        """Registers the session in DragonflyDB."""
        try:
            key = f"session:{self.session_id}:meta"
            data = {
                "project_id": self.project_id,
                "agent_id": self.agent_id,
                "cwd": self.cwd,
                "status": "active",
                "pid": os.getpid(),
            }
            self.redis.set(key, json.dumps(data))
            # Set a long expiry (e.g., 7 days)
            self.redis.expire(key, 60 * 60 * 24 * 7)
            print(f"[SessionManager] Session {self.session_id} registered.")
        except Exception as e:
            print(f"[SessionManager] Warning: Could not register session: {e}")

    def get_session_id(self):
        return self.session_id

    def generate_trace_id(self):
        """Generates a UUID for tracing."""
        return f"trace-{uuid.uuid4()}"

    def log_activity(self, activity_type, details):
        """Logs activity to DragonflyDB for history."""
        try:
            key = f"session:{self.session_id}:history"
            entry = {
                "timestamp": str(uuid.uuid1().time),  # simple timestamp
                "type": activity_type,
                "details": details,
                "trace_id": self.generate_trace_id(),
            }
            # Push to a list
            self.redis.rpush(key, json.dumps(entry))
        except Exception as e:
            pass  # Fail silently for logging


# Global instance
_session_manager = None


def get_session_manager():
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
