from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PostgresStatus(BaseModel):
    is_connected: bool
    version: Optional[str] = None
    uptime: Optional[str] = None
    current_connections: Optional[int] = None
    active_connections: Optional[int] = None
    max_connections: Optional[int] = None
    connection_usage_percent: Optional[float] = None
    database_size: Optional[str] = None
    tables_count: Optional[int] = None
    error_message: Optional[str] = None
    detailed_stats: Optional[Dict[str, Any]] = None


class TaskConsumerStatus(BaseModel):
    boot_at: str
    current: Dict[str, Any] = {}
    done: int
    failed: int
    lag: int
    name: str
    now: str
    pending: int


class KnowledgeStatus(BaseModel):
    database: Optional[Dict[str, Any]] = None
    doc_engine: Optional[Dict[str, Any]] = None
    redis: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    task_executor_heartbeats: Optional[Dict[str, List[TaskConsumerStatus]]] = None


class SystemStatus(BaseModel):
    postgres_online: bool = False
    knowledge_online: bool = False
