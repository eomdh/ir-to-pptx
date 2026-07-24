"""레이아웃 엔진 — 마크다운을 좌표까지 박힌 평면 IR 로 바꾼다.

이 파일이 이 repo 의 코어다. 하는 일은 딱 하나: 블록 목록을 받아 슬라이드마다
요소를 절대좌표(인치)로 놓고, 세로로 넘치면 다음 슬라이드로 이어붙인다.

결정적이다 — 같은 마크다운은 항상 같은 IR 을 낸다(랜덤·시간·해시순서 의존 없음).
그게 "화면 미리보기와 pptx 파일이 같다"의 근거다.

의도적 한계: 텍스트 줄바꿈(wrap) 을 측정하지 않는다. 불릿·문단은 한 줄 높이를
예산으로 잡는다. 폰트 메트릭 엔진을 두는 건 이 데모의 목적(한 가지 어려운 걸
증명) 대비 과하다. 아주 긴 한 줄이 박스 안에서 시각적으로 접히면 세로가 약간
촘촘해질 수 있고, 그건 README 한계에 적는다.
"""

from __future__ import annotations

from typing import NamedTuple

from ir_pptx.blocks import (
    Block,
    Bullet,
    Chart,
    Columns,
    Heading,
    Image,
    Kpi,
    Paragraph,
    parse_markdown,
)
from ir_pptx.ir import (
    Deck,
    ImageElement,
    ShapeElement,
    Slide,
    TextElement,
)

# 슬라이드(16:9). pptxgenjs 기본 레이아웃과 같은 값.
SLIDE_W = 10.0
SLIDE_H = 5.625

MARGIN_X = 0.6
CONTENT_W = SLIDE_W - 2 * MARGIN_X  # 8.8
COL_GAP = 0.3  # 2단 컬럼 사이 간격


class Region(NamedTuple):
    """블록을 놓을 가로 영역. x = 왼쪽 좌표, w = 너비."""

    x: float
    w: float

# 제목 영역
TITLE_Y = 0.45
TITLE_H = 0.8
TITLE_SIZE = 28
ACCENT_Y = TITLE_Y + TITLE_H + 0.05
ACCENT_W = 1.6
ACCENT_H = 0.06

# 본문 영역
CONTENT_TOP = 1.55
CONTENT_BOTTOM = SLIDE_H - 0.4  # 5.225
SUBHEAD_SIZE = 18
SUBHEAD_H = 0.42
SUBHEAD_TOP_GAP = 0.12
BULLET_INDENT = 0.35
BULLET_SIZE = 16
BULLET_LINE_H = 0.42
PARA_SIZE = 16
PARA_LINE_H = 0.4
BLOCK_GAP = 0.18  # 이미지·차트 아래 여백
IMAGE_H = 3.0
CHART_H = 3.2

# KPI 지표 타일
KPI_H = 1.15
KPI_GAP = 0.22
KPI_PAD = 0.22

COLOR_TITLE = "12213A"
COLOR_TEXT = "1A1A1A"
COLOR_ACCENT = "2563EB"
COLOR_CARD = "F2F4F6"
COLOR_VALUE = "191F28"
COLOR_MUTED = "6B7684"
COLOR_UP = "16A34A"
COLOR_DOWN = "DC2626"

FULL_REGION = Region(MARGIN_X, CONTENT_W)


def layout(markdown: str) -> Deck:
    """마크다운 → Deck(평면 IR)."""
    deck = Deck(width=SLIDE_W, height=SLIDE_H)
    for title, body in _sections(parse_markdown(markdown)):
        _emit_section(deck, title, body)
    return deck


def _sections(blocks: list[Block]) -> list[tuple[str | None, list[Block]]]:
    """H1('#') 경계로 (제목, 본문블록들) 묶음을 만든다.

    첫 H1 앞에 내용이 있으면 제목 없는 섹션 하나로 담는다.
    """
    sections: list[tuple[str | None, list[Block]]] = []
    title: str | None = None
    body: list[Block] = []
    started = False

    for b in blocks:
        if isinstance(b, Heading) and b.level == 1:
            if started:
                sections.append((title, body))
            title, body, started = b.text, [], True
        else:
            started = True
            body.append(b)
    if started:
        sections.append((title, body))
    return sections


def _emit_section(deck: Deck, title: str | None, body: list[Block]) -> None:
    slide = _new_slide(deck, title)
    cursor = CONTENT_TOP
    for block in body:
        h = _block_height(block)
        # 현재 슬라이드에 이미 뭔가 놓였는데 다음 블록이 안 맞으면 이어지는 슬라이드로.
        if cursor + h > CONTENT_BOTTOM and cursor > CONTENT_TOP:
            slide = _new_slide(deck, _continued(title))
            cursor = CONTENT_TOP
        _place(slide, block, cursor, FULL_REGION)
        cursor += h


def _new_slide(deck: Deck, title: str | None) -> Slide:
    slide = Slide()
    if title is not None:
        slide.elements.append(
            TextElement(
                x=_r(MARGIN_X),
                y=_r(TITLE_Y),
                w=_r(CONTENT_W),
                h=_r(TITLE_H),
                z=1,
                text=title,
                size=TITLE_SIZE,
                bold=True,
                color=COLOR_TITLE,
                align="left",
            )
        )
        slide.elements.append(
            ShapeElement(
                x=_r(MARGIN_X),
                y=_r(ACCENT_Y),
                w=_r(ACCENT_W),
                h=_r(ACCENT_H),
                z=0,
                shape="rect",
                fill=COLOR_ACCENT,
            )
        )
    deck.slides.append(slide)
    return slide


def _block_height(block: Block) -> float:
    if isinstance(block, Heading):
        return SUBHEAD_TOP_GAP + SUBHEAD_H
    if isinstance(block, Bullet):
        return BULLET_LINE_H
    if isinstance(block, Paragraph):
        return PARA_LINE_H
    if isinstance(block, Image):
        return IMAGE_H + BLOCK_GAP
    if isinstance(block, Chart):
        return CHART_H + BLOCK_GAP
    if isinstance(block, Kpi):
        return KPI_H + BLOCK_GAP
    if isinstance(block, Columns):
        # 가장 높은 칸이 이 블록의 높이가 된다.
        return max((_column_height(col) for col in block.columns), default=0.0)
    return 0.0


def _column_height(blocks: list[Block]) -> float:
    return sum(_block_height(b) for b in blocks)


def _flow(slide: Slide, blocks: list[Block], region: Region, start_y: float) -> float:
    # 한 영역 안에서 블록을 위에서 아래로 놓는다. 페이지 넘김은 없다(컬럼 안쪽용).
    cursor = start_y
    for block in blocks:
        _place(slide, block, cursor, region)
        cursor += _block_height(block)
    return cursor


def _place(slide: Slide, block: Block, y: float, region: Region) -> None:
    if isinstance(block, Heading):
        # 본문 소제목(H2 이하). 슬라이드를 여는 H1 은 _sections 에서 걸러졌다.
        slide.elements.append(
            TextElement(
                x=_r(region.x),
                y=_r(y + SUBHEAD_TOP_GAP),
                w=_r(region.w),
                h=_r(SUBHEAD_H),
                z=1,
                text=block.text,
                size=SUBHEAD_SIZE,
                bold=True,
                color=COLOR_TITLE,
                align="left",
            )
        )
    elif isinstance(block, Bullet):
        indent = BULLET_INDENT * (block.level + 1)
        slide.elements.append(
            TextElement(
                x=_r(region.x + indent),
                y=_r(y),
                w=_r(region.w - indent),
                h=_r(BULLET_LINE_H),
                z=1,
                text=block.text,
                size=BULLET_SIZE,
                color=COLOR_TEXT,
                align="left",
                bullet=True,
            )
        )
    elif isinstance(block, Paragraph):
        slide.elements.append(
            TextElement(
                x=_r(region.x),
                y=_r(y),
                w=_r(region.w),
                h=_r(PARA_LINE_H),
                z=1,
                text=block.text,
                size=PARA_SIZE,
                color=COLOR_TEXT,
                align="left",
            )
        )
    elif isinstance(block, Image):
        slide.elements.append(
            ImageElement(
                x=_r(region.x),
                y=_r(y),
                w=_r(region.w),
                h=_r(IMAGE_H),
                z=1,
                src=block.src,
            )
        )
    elif isinstance(block, Chart):
        # 차트는 프론트가 그리므로 여기선 자리와 spec 만 넘긴다.
        from ir_pptx.ir import ChartElement

        slide.elements.append(
            ChartElement(
                x=_r(region.x),
                y=_r(y),
                w=_r(region.w),
                h=_r(CHART_H),
                z=1,
                spec=block.spec,
            )
        )
    elif isinstance(block, Kpi):
        _place_kpi(slide, block, y, region)
    elif isinstance(block, Columns):
        _place_columns(slide, block, y, region)


def _place_columns(slide: Slide, block: Columns, y: float, region: Region) -> None:
    n = len(block.columns)
    if n == 0:
        return
    col_w = (region.w - (n - 1) * COL_GAP) / n
    for i, col in enumerate(block.columns):
        col_x = region.x + i * (col_w + COL_GAP)
        _flow(slide, col, Region(col_x, col_w), y)


def _place_kpi(slide: Slide, block: Kpi, y: float, region: Region) -> None:
    n = len(block.tiles)
    if n == 0:
        return
    tile_w = (region.w - (n - 1) * KPI_GAP) / n
    inner_w = tile_w - 2 * KPI_PAD
    for i, tile in enumerate(block.tiles):
        tile_x = region.x + i * (tile_w + KPI_GAP)
        # 카드 배경
        slide.elements.append(
            ShapeElement(
                x=_r(tile_x),
                y=_r(y),
                w=_r(tile_w),
                h=_r(KPI_H),
                z=0,
                shape="roundRect",
                fill=COLOR_CARD,
            )
        )
        # 큰 값
        slide.elements.append(
            TextElement(
                x=_r(tile_x + KPI_PAD),
                y=_r(y + 0.22),
                w=_r(inner_w),
                h=_r(0.5),
                z=1,
                text=tile.value,
                size=24,
                bold=True,
                color=COLOR_VALUE,
                align="left",
            )
        )
        # 라벨(왼쪽)
        slide.elements.append(
            TextElement(
                x=_r(tile_x + KPI_PAD),
                y=_r(y + 0.74),
                w=_r(inner_w),
                h=_r(0.28),
                z=1,
                text=tile.label,
                size=12,
                color=COLOR_MUTED,
                align="left",
            )
        )
        # delta(오른쪽, 부호로 색을 고른다)
        if tile.delta:
            slide.elements.append(
                TextElement(
                    x=_r(tile_x + KPI_PAD),
                    y=_r(y + 0.74),
                    w=_r(inner_w),
                    h=_r(0.28),
                    z=1,
                    text=tile.delta,
                    size=12,
                    bold=True,
                    color=_delta_color(tile.delta),
                    align="right",
                )
            )


def _delta_color(delta: str) -> str:
    if delta.startswith("+"):
        return COLOR_UP
    if delta.startswith("-"):
        return COLOR_DOWN
    return COLOR_MUTED


def _continued(title: str | None) -> str | None:
    if title is None:
        return None
    return f"{title} (계속)"


def _r(value: float) -> float:
    # 좌표를 일정 자리로 반올림해 결정성과 깔끔한 값을 함께 얻는다.
    return round(value, 3)
