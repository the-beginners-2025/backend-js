from pydantic import BaseModel


class OCRResponse(BaseModel):
    content: str
    confidence: float
