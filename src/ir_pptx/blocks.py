"""마크다운 → 블록 목록.

렉싱(토큰화)은 검증된 markdown-it 에 맡기고, 여기서는 그 토큰 스트림에서
레이아웃이 다룰 최소 단위(블록)만 뽑는다. 좌표 계산은 하지 않는다 — 그건
layout 의 몫이다. 이 분리 덕에 "어려운 부분"이 마크다운 재파싱이 아니라
레이아웃(좌표)에 남는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from markdown_it import MarkdownIt

from ir_pptx.ir import ChartSpec


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Bullet:
    text: str
    level: int = 0  # 중첩 깊이(0 = 최상위)


@dataclass
class Paragraph:
    text: str


@dataclass
class Image:
    src: str
    alt: str = ""


@dataclass
class Chart:
    spec: ChartSpec


@dataclass
class KpiTile:
    label: str
    value: str
    delta: str | None = None


@dataclass
class Kpi:
    tiles: list[KpiTile]


Block = Heading | Bullet | Paragraph | Image | Chart | Kpi

_md = MarkdownIt("commonmark")


def parse_markdown(text: str) -> list[Block]:
    tokens = _md.parse(text)
    blocks: list[Block] = []

    list_depth = 0
    heading_level = 1
    mode: str | None = None  # 바로 뒤 inline 토큰을 무엇으로 읽을지

    for tok in tokens:
        t = tok.type
        if t in ("bullet_list_open", "ordered_list_open"):
            list_depth += 1
        elif t in ("bullet_list_close", "ordered_list_close"):
            list_depth -= 1
        elif t == "heading_open":
            heading_level = int(tok.tag[1])  # 'h1' → 1
            mode = "heading"
        elif t == "paragraph_open":
            # 리스트 안의 문단은 불릿 한 줄이다.
            mode = "bullet" if list_depth > 0 else "para"
        elif t == "fence":
            info = tok.info.strip()
            if info == "chart":
                blocks.append(Chart(spec=_parse_chart(tok.content)))
            elif info == "kpi":
                blocks.append(_parse_kpi(tok.content))
        elif t == "inline":
            _emit_inline(blocks, tok, mode, list_depth, heading_level)
            mode = None

    return blocks


def _emit_inline(blocks, tok, mode, list_depth, heading_level):
    if mode == "heading":
        blocks.append(Heading(level=heading_level, text=_inline_text(tok)))
    elif mode == "bullet":
        blocks.append(Bullet(text=_inline_text(tok), level=max(0, list_depth - 1)))
    elif mode == "para":
        img = _first_image(tok)
        if img is not None:
            blocks.append(Image(src=img[0], alt=img[1]))
        else:
            text = _inline_text(tok)
            if text:
                blocks.append(Paragraph(text=text))


def _inline_text(tok) -> str:
    parts: list[str] = []
    for child in tok.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts).strip()


def _first_image(tok) -> tuple[str, str] | None:
    for child in tok.children or []:
        if child.type == "image":
            return (child.attrGet("src") or "", child.content or "")
    return None


def _parse_chart(raw: str) -> ChartSpec:
    # 잘못된 차트 JSON 은 pydantic 이 걸러 명확한 에러로 올린다(API 는 400 으로 변환).
    return ChartSpec.model_validate(json.loads(raw))


def _parse_kpi(raw: str) -> Kpi:
    data = json.loads(raw)
    tiles = [
        KpiTile(
            label=str(item.get("label", "")),
            value=str(item.get("value", "")),
            delta=str(item["delta"]) if item.get("delta") is not None else None,
        )
        for item in data
    ]
    return Kpi(tiles=tiles)
