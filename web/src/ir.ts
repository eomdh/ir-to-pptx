// 평면 IR 계약의 TS 미러. 백엔드 src/ir_pptx/ir.py 와 1:1 로 맞춘다.
//
// 단위 = 인치, 원점 = 슬라이드 좌상단. 색은 '#' 없는 6자리 hex.
// 이 파일이 미리보기(preview)와 파일 생성(pptx) 두 렌더러의 공통 입력이라,
// 여기 타입이 곧 "보이는 것과 나오는 것이 같다"의 컴파일 타임 보증이다.

export type Align = "left" | "center" | "right";

// 글상자 안 한 조각. runs 가 있을 때 인라인 강조(굵게/기울임)를 조각별로 그린다.
export interface TextRun {
  text: string;
  bold: boolean;
  italic: boolean;
}

export interface TextElement {
  type: "text";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  text: string;
  runs: TextRun[] | null;
  size: number; // pt
  bold: boolean;
  italic: boolean;
  color: string;
  align: Align;
  bullet: boolean;
}

export interface ShapeElement {
  type: "shape";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  shape: "rect" | "roundRect" | "line";
  fill: string;
}

export interface ImageElement {
  type: "image";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  src: string;
}

export interface ChartSeries {
  name: string;
  data: number[];
}

export interface ChartSpec {
  kind: "bar" | "line" | "pie";
  title?: string | null;
  categories: string[];
  series: ChartSeries[];
}

export interface ChartElement {
  type: "chart";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  spec: ChartSpec;
}

// type 판별자 union. switch(el.type) 로 빠짐없는 디스패치가 된다.
export type Element = TextElement | ShapeElement | ImageElement | ChartElement;

export interface Slide {
  elements: Element[];
}

export interface Deck {
  width: number;
  height: number;
  slides: Slide[];
}
