import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv


@dataclass
class Result:
    content: str
    confidence: float


class OCRService:
    def __init__(self, token: str, endpoint: str):
        self._endpoint = endpoint
        self._session = requests.Session()
        self._session.headers.update(
            {
                "token": token,
            }
        )

    def normal_ocr(self, image_data: bytes) -> Result:
        response = self._session.post(
            url=f"{self._endpoint}/latex_ocr",
            files={"file": image_data},
        )

        if not response.ok:
            raise Exception("OCR service error")

        data = response.json()
        if not data["status"]:
            raise Exception("OCR failed")

        return Result(content=data["res"]["latex"], confidence=data["res"]["conf"])

    def turbo_ocr(self, image_data: bytes) -> Result:
        response = self._session.post(
            url=f"{self._endpoint}/latex_ocr_turbo",
            files={"file": image_data},
        )

        if not response.ok:
            raise Exception("OCR service error")

        data = response.json()
        if not data["status"]:
            raise Exception("OCR failed")

        return Result(content=data["res"]["latex"], confidence=data["res"]["conf"])


if __name__ == "__main__":
    load_dotenv()
    ocr_service = OCRService(os.getenv("OCR_TOKEN"), os.getenv("OCR_ENDPOINT"))

    print("Testing OCR service...")
    result = ocr_service.normal_ocr(open("../test_input/ocr.png", "rb").read())
    print(f"Result: {result.content}")
    print(f"Confidence: {result.confidence}")

    print("Testing Turbo OCR service...")
    result = ocr_service.turbo_ocr(open("../test_input/ocr.png", "rb").read())
    print(f"Result: {result.content}")
    print(f"Confidence: {result.confidence}")
