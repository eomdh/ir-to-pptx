"""평면 IR — 이 프로젝트의 계약(contract).

레이아웃 엔진의 출력이자 프론트 두 렌더러(DOM 미리보기 · pptxgenjs)의 입력이다.
"평면"은 두 가지를 뜻한다:

  1. 좌표가 이미 다 박혀 있다. 요소마다 x/y/w/h 가 절대값이라, 받는 쪽은
     레이아웃을 다시 계산하지 않고 그 자리에 그리기만 한다.
  2. 중첩이 없다. Deck → Slide → Element[] 3단이 끝이고, 요소는 서로를
     품지 않는다. 그래서 렌더러가 요소 리스트를 z 순으로 한 번 훑으면 된다.

좌표계 규약:
  단위 = 인치. 원점 = 슬라이드 좌상단. x 는 오른쪽, y 는 아래로 증가한다.
  PowerPoint · pptxgenjs 와 같은 규약이라 프론트에서 단위 변환이 없다
  (DOM 미리보기만 인치 → px 로 스케일한다).

색은 '#' 없는 6자리 hex 로 담는다. pptxgenjs 가 그 형태를 그대로 받기 때문이고,
DOM 쪽에서만 앞에 '#' 를 붙인다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Align = Literal["left", "center", "right"]


class TextRun(BaseModel):
    """글상자 안 한 조각. 인라인 강조(굵게/기울임)가 섞인 줄을 조각들로 나눠 담는 단위."""

    text: str
    bold: bool = False
    italic: bool = False


class TextElement(BaseModel):
    """글상자 하나. 불릿 한 줄도 이 요소 하나로 표현한다(줄마다 y 가 다르다).

    `runs` 가 있으면 조각별 강조로 그리고, 없으면 `text` 를 요소 단위 bold/italic 으로 그림.
    `runs` 가 있을 때도 `text` 는 조각을 이어붙인 평문이라 줄 수 계산과 폴백에 쓰임.
    """

    type: Literal["text"] = "text"
    x: float
    y: float
    w: float
    h: float
    z: int = 0
    text: str
    runs: list[TextRun] | None = None
    size: float  # pt
    bold: bool = False
    italic: bool = False
    color: str = "1A1A1A"
    align: Align = "left"
    bullet: bool = False


class ShapeElement(BaseModel):
    """단색 도형. 제목 밑 강조 바, KPI 타일·표 헤더 배경 같은 장식에 쓴다."""

    type: Literal["shape"] = "shape"
    x: float
    y: float
    w: float
    h: float
    z: int = 0
    shape: Literal["rect", "roundRect", "line"] = "rect"
    fill: str = "2563EB"


class ImageElement(BaseModel):
    """이미지. src 는 URL 또는 data URI."""

    type: Literal["image"] = "image"
    x: float
    y: float
    w: float
    h: float
    z: int = 0
    src: str


class ChartSeries(BaseModel):
    name: str = ""
    data: list[float] = Field(default_factory=list)


class ChartSpec(BaseModel):
    """렌더러 중립 차트 기술. 백엔드는 ECharts 를 모른다.

    프론트가 이 spec 을 ECharts 옵션으로 옮겨 화면 밖에서 렌더 → PNG 로 캡처 →
    이미지로 슬라이드에 얹는다(원본의 isChartCapture 패턴). 백엔드가 raw ECharts
    옵션을 내려주지 않는 이유: IR 이 특정 차트 라이브러리에 묶이면 계약이 깨진다.
    """

    kind: Literal["bar", "line", "pie"]
    title: str | None = None
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)


class ChartElement(BaseModel):
    """차트가 놓일 자리와 spec. 픽셀은 프론트가 채운다."""

    type: Literal["chart"] = "chart"
    x: float
    y: float
    w: float
    h: float
    z: int = 0
    spec: ChartSpec


# type 을 판별자로 둔 discriminated union. 프론트에서 switch(el.type) 로
# 빠짐없는(exhaustive) 디스패치가 되고, pydantic 은 역직렬화 때 이 필드로
# 정확한 모델을 고른다.
Element = Annotated[
    TextElement | ShapeElement | ImageElement | ChartElement,
    Field(discriminator="type"),
]


class Slide(BaseModel):
    elements: list[Element] = Field(default_factory=list)


class Deck(BaseModel):
    # 16:9 기본. pptxgenjs 의 기본 레이아웃(10 x 5.625 in)과 같은 값이다.
    width: float = 10.0
    height: float = 5.625
    slides: list[Slide] = Field(default_factory=list)
