"""마크다운 → 블록 목록.

렉싱(토큰화)은 검증된 markdown-it 에 맡기고, 여기서는 그 토큰 스트림에서
레이아웃이 다룰 최소 단위(블록)만 뽑는다. 좌표 계산은 하지 않는다 — 그건
layout 의 몫이다. 이 분리 덕에 "어려운 부분"이 마크다운 재파싱이 아니라
레이아웃(좌표)에 남는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from markdown_it import MarkdownIt

from ir_pptx.ir import ChartSpec, TextRun


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Bullet:
    text: str  # 조각을 이어붙인 평문(줄 수 계산과 폴백용)
    runs: list[TextRun] = field(default_factory=list)  # 인라인 강조가 담긴 조각들
    level: int = 0  # 중첩 깊이(0 = 최상위)


@dataclass
class Paragraph:
    text: str
    runs: list[TextRun] = field(default_factory=list)


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


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]


@dataclass
class Columns:
    columns: list[list[Block]]


Block = Heading | Bullet | Paragraph | Image | Chart | Kpi | Table | Columns

# commonmark 프리셋은 표를 끄므로 명시적으로 켠다.
_md = MarkdownIt("commonmark").enable("table")


def parse_markdown(text: str) -> list[Block]:
    # 컬럼 영역(::: columns ... :::)만 먼저 떼어내 각 칸을 따로 파싱하고,
    # 나머지 보통 텍스트는 markdown-it 로 파싱한다.
    blocks: list[Block] = []
    for kind, payload in _segments(text):
        if kind == "columns":
            blocks.append(Columns(columns=[_parse_plain(part) for part in payload]))
        else:
            blocks.extend(_parse_plain(payload))
    return blocks


def _segments(text: str):
    # ("text", 문자열) 또는 ("columns", [칸별 문자열]) 을 문서 순서대로 낸다.
    # 칸 구분은 || 한 줄, 블록 여닫이는 ::: columns / ::: 한 줄이다.
    lines = text.split("\n")
    buf: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "::: columns":
            if buf:
                yield ("text", "\n".join(buf))
                buf = []
            i += 1
            cols: list[list[str]] = [[]]
            while i < len(lines) and lines[i].strip() != ":::":
                if lines[i].strip() == "||":
                    cols.append([])
                else:
                    cols[-1].append(lines[i])
                i += 1
            i += 1  # 닫는 ::: 건너뛰기
            yield ("columns", ["\n".join(c) for c in cols])
        else:
            buf.append(lines[i])
            i += 1
    if buf:
        yield ("text", "\n".join(buf))


def _parse_plain(text: str) -> list[Block]:
    tokens = _md.parse(text)
    blocks: list[Block] = []

    list_depth = 0
    heading_level = 1
    mode: str | None = None  # 바로 뒤 inline 토큰을 무엇으로 읽을지

    # 표 상태
    section = "body"
    header: list[str] = []
    rows: list[list[str]] = []
    row: list[str] = []

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
        elif t == "table_open":
            section, header, rows = "body", [], []
        elif t == "thead_open":
            section = "head"
        elif t == "tbody_open":
            section = "body"
        elif t == "tr_open":
            row = []
        elif t in ("th_open", "td_open"):
            mode = "cell"
        elif t == "tr_close":
            if section == "head":
                header = row
            else:
                rows.append(row)
        elif t == "table_close":
            blocks.append(Table(header=header, rows=rows))
        elif t == "inline":
            if mode == "cell":
                row.append(_inline_text(tok))
            else:
                _emit_inline(blocks, tok, mode, list_depth, heading_level)
            mode = None

    return blocks


def _emit_inline(blocks, tok, mode, list_depth, heading_level):
    if mode == "heading":
        blocks.append(Heading(level=heading_level, text=_inline_text(tok)))
    elif mode == "bullet":
        runs = _inline_runs(tok)
        blocks.append(Bullet(text=_join(runs), runs=runs, level=max(0, list_depth - 1)))
    elif mode == "para":
        img = _first_image(tok)
        if img is not None:
            blocks.append(Image(src=img[0], alt=img[1]))
        else:
            runs = _inline_runs(tok)
            text = _join(runs)
            if text:
                blocks.append(Paragraph(text=text, runs=runs))


def _inline_runs(tok) -> list[TextRun]:
    # inline 자식을 훑어 강조(strong/em) 깊이를 세며 같은 스타일끼리 조각으로 묶는다.
    runs: list[TextRun] = []
    bold = 0
    italic = 0

    def push(text: str) -> None:
        if not text:
            return
        b, i = bold > 0, italic > 0
        if runs and runs[-1].bold == b and runs[-1].italic == i:
            runs[-1].text += text  # 같은 스타일이면 앞 조각에 이어붙임
        else:
            runs.append(TextRun(text=text, bold=b, italic=i))

    for child in tok.children or []:
        ct = child.type
        if ct == "strong_open":
            bold += 1
        elif ct == "strong_close":
            bold -= 1
        elif ct == "em_open":
            italic += 1
        elif ct == "em_close":
            italic -= 1
        elif ct in ("text", "code_inline"):
            push(child.content)
        elif ct in ("softbreak", "hardbreak"):
            push(" ")

    # 앞뒤 공백 정리: 첫 조각 왼쪽, 마지막 조각 오른쪽. 빈 조각은 버림.
    if runs:
        runs[0].text = runs[0].text.lstrip()
        runs[-1].text = runs[-1].text.rstrip()
        runs = [r for r in runs if r.text]
    return runs


def _join(runs: list[TextRun]) -> str:
    return "".join(r.text for r in runs)


def _inline_text(tok) -> str:
    # 강조를 버린 평문. 제목과 표 셀처럼 조각별 스타일이 필요 없는 곳에서 씀.
    return _join(_inline_runs(tok))


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
