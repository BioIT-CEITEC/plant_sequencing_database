import uuid
from typing import Dict, Any, Optional
from core.contracts import DocumentSession

class SessionManager:
    """Manages the in-memory or persisted session state. 
    In a real scaled app, this would use Redis. For now, we simulate in-memory/Flask-session bridging.
    """
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def create(self, session_dict: Dict) -> str:
        session_id = str(uuid.uuid4())
        session_dict["session_id"] = session_id
        session_dict["chat_history"] = []
        session_dict["extracted_metadata"] = {}
        session_dict["document_filename"] = None
        session_dict["chunk_count"] = 0
        return session_id

    def update(self, session_dict: Dict, **kwargs):
        for k, v in kwargs.items():
            session_dict[k] = v

    def clear_document(self, session_dict: Dict):
        session_id = session_dict.get("session_id")
        if session_id:
            try:
                self.vector_store.delete_collection(session_id)
            except Exception:
                pass
        session_dict["document_filename"] = None
        session_dict["chunk_count"] = 0
        session_dict["extracted_metadata"] = {}
        session_dict["chat_history"] = []
