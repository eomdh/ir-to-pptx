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

from ir_pptx.blocks import Block, Bullet, Chart, Heading, Image, Paragraph, parse_markdown
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

COLOR_TITLE = "12213A"
COLOR_TEXT = "1A1A1A"
COLOR_ACCENT = "2563EB"


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
        _place(slide, block, cursor)
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
    return 0.0


def _place(slide: Slide, block: Block, y: float) -> None:
    if isinstance(block, Heading):
        # 본문 소제목(H2 이하). 슬라이드를 여는 H1 은 _sections 에서 걸러졌다.
        slide.elements.append(
            TextElement(
                x=_r(MARGIN_X),
                y=_r(y + SUBHEAD_TOP_GAP),
                w=_r(CONTENT_W),
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
                x=_r(MARGIN_X + indent),
                y=_r(y),
                w=_r(CONTENT_W - indent),
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
                x=_r(MARGIN_X),
                y=_r(y),
                w=_r(CONTENT_W),
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
                x=_r(MARGIN_X),
                y=_r(y),
                w=_r(CONTENT_W),
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
                x=_r(MARGIN_X),
                y=_r(y),
                w=_r(CONTENT_W),
                h=_r(CHART_H),
                z=1,
                spec=block.spec,
            )
        )


def _continued(title: str | None) -> str | None:
    if title is None:
        return None
    return f"{title} (계속)"


def _r(value: float) -> float:
    # 좌표를 일정 자리로 반올림해 결정성과 깔끔한 값을 함께 얻는다.
    return round(value, 3)
