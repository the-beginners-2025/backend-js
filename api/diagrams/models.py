from typing import List, Optional

from pydantic import BaseModel, Field


class DiagramRequest(BaseModel):
    assistant_content: str
    user_content: str


class FlowchartResponse(BaseModel):
    mermaid: str


class Node(BaseModel):
    text: str
    nodes: Optional[List["Node"]] = None


Node.model_rebuild()


class MindmapResponse(BaseModel):
    root_node: Node
