"""FastAPI 앱. 하는 일은 둘뿐이다.

  POST /ir  : 마크다운을 받아 좌표까지 박힌 평면 IR(Deck)로 돌려준다.
  그 외 경로: 빌드된 프론트를 정적으로 서빙한다(도커 이미지 안에서만 존재).

파일 생성은 여기 없다. 서버는 좌표만 계산하고, .pptx 는 브라우저가 만든다.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from ir_pptx.ir import Deck
from ir_pptx.layout import layout

app = FastAPI(title="ir-to-pptx")


class RenderRequest(BaseModel):
    markdown: str


@app.post("/ir")
def to_ir(req: RenderRequest) -> Deck:
    try:
        return layout(req.markdown)
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        # 대개 차트 펜스의 JSON 이 깨졌을 때. 서버 잘못이 아니라 입력 잘못이므로 400.
        detail = f"마크다운을 IR 로 바꾸지 못했다: {exc}"
        raise HTTPException(status_code=400, detail=detail) from exc


# 도커 이미지에서는 빌드된 프론트가 /app/web-dist 에 온다. dev 에선 vite 가 프론트를
# 따로 서빙하므로 이 디렉토리가 없고, 그때는 마운트를 건너뛴다.
_web_dist = Path(__file__).resolve().parents[2] / "web-dist"
if _web_dist.is_dir():
    app.mount("/", StaticFiles(directory=_web_dist, html=True), name="web")
