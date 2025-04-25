import json
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.diagrams.models import DiagramRequest, FlowchartResponse, MindmapResponse, Node
from db.database import get_db
from db.models import User, UserStatistics
from middlewares.auth import auth_middleware
from services.llm_service import Message, Role
from services.uni import LLM_MODEL, llm_service

router = APIRouter(prefix="/diagrams")

with open("prompts/flowchart.txt", "r", encoding="utf-8") as f:
    FLOWCHART_PROMPT = f.read()
with open("prompts/mindmap.txt", "r", encoding="utf-8") as f:
    MINDMAP_PROMPT = f.read()


@router.post("/mindmap", response_model=MindmapResponse)
async def create_mindmap(
    diagram_request: DiagramRequest, user: User = Depends(auth_middleware), db:Session = Depends(get_db)
):
    usere_stats = (
        db.query(UserStatistics).filter(UserStatistics.user_id == user.id).first()
    )
    usere_stats.mind_map_count += 1
    db.commit()

    messages = [
        Message(
            role=Role.SYSTEM,
            content=MINDMAP_PROMPT,
        ),
        Message(
            role=Role.USER,
            content=f"问题: {diagram_request.user_content}\n回答: {diagram_request.assistant_content}",
        ),
    ]
    response = llm_service.chat(
        model=LLM_MODEL,
        messages=messages,
    )

    def parse_node(xml_node):
        node = Node(text=xml_node.get("text"))
        children = []
        for child in xml_node.findall("node"):
            children.append(parse_node(child))
        if children:
            node.nodes = children
        return node

    try:
        root = ET.fromstring(response.content)
        root_node = root.find("node")
        if root_node is not None:
            parsed_root = parse_node(root_node)
            return MindmapResponse(root_node=parsed_root)
        else:
            return MindmapResponse(root_node=Node(text="解析失败"))
    except Exception as e:
        return MindmapResponse(root_node=Node(text=f"解析错误: {str(e)}"))


@router.post("/flowchart")
async def create_flowchart(
    diagram_request: DiagramRequest, user: User = Depends(auth_middleware), db: Session = Depends(get_db)
):
    usere_stats = (
        db.query(UserStatistics).filter(UserStatistics.user_id == user.id).first()
    )
    usere_stats.flow_chart_count += 1
    db.commit()

    messages = [
        Message(
            role=Role.SYSTEM,
            content=FLOWCHART_PROMPT,
        ),
        Message(
            role=Role.USER,
            content=f"问题: {diagram_request.user_content}\n回答: {diagram_request.assistant_content}",
        ),
    ]
    response = llm_service.chat_stream(
        model=LLM_MODEL,
        messages=messages,
    )

    async def event_stream():
        for chunk in response:
            data = {
                "content": chunk.content,
            }
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(
        content=event_stream(),
        media_type="text/event-stream",
    )
