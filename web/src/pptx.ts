// IR → pptxgenjs 디스패치. 레이아웃 엔진의 짝이다.
//
// 백엔드가 좌표를 다 계산해 놨으므로 여기서 하는 일은 "요소 타입을 pptxgenjs
// 호출로 옮기는 것"뿐이다. 좌표 계산은 없다. 인치 단위라 변환도 없다.
//
// 실제 pptxgen 인스턴스가 아니라 최소 sink 인터페이스에 대고 짜서, 브라우저를
// 안 띄우고도 디스패치를 단위 테스트할 수 있게 한다(buildPptx 에서만 진짜 pptxgen 에 붙인다).

import pptxgen from "pptxgenjs";
import type { Align, ChartElement, Deck, Element, Slide } from "./ir";

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface TextOpts extends Box {
  fontSize: number;
  bold: boolean;
  color: string;
  align: Align;
  bullet: boolean;
}

export interface ImageOpts extends Box {
  data?: string;
  path?: string;
}

export interface ShapeOpts extends Box {
  fill: { color: string };
}

// pptxgen.Slide 중 우리가 쓰는 부분만. 테스트는 이걸 가짜로 구현한다.
export interface SlideSink {
  addText(text: string, opts: TextOpts): void;
  addImage(opts: ImageOpts): void;
  addShape(shape: string, opts: ShapeOpts): void;
}

// 차트 요소를 실제 PNG(data URI)로 바꾸는 건 프론트(ECharts)의 몫이라 밖에서 주입한다.
export type ResolveChart = (el: ChartElement) => string;

export function placeElement(slide: SlideSink, el: Element, resolveChart: ResolveChart): void {
  const box: Box = { x: el.x, y: el.y, w: el.w, h: el.h };
  switch (el.type) {
    case "text":
      slide.addText(el.text, {
        ...box,
        fontSize: el.size,
        bold: el.bold,
        color: el.color,
        align: el.align,
        bullet: el.bullet,
      });
      break;
    case "shape":
      slide.addShape(el.shape, { ...box, fill: { color: el.fill } });
      break;
    case "image":
      // data URI 는 data, 외부 URL 은 path 로 넣는다(pptxgenjs 규약).
      slide.addImage(
        el.src.startsWith("data:") ? { ...box, data: el.src } : { ...box, path: el.src },
      );
      break;
    case "chart":
      slide.addImage({ ...box, data: resolveChart(el) });
      break;
    default: {
      // union 이 늘면 여기서 컴파일이 깨져 디스패치 누락을 잡는다.
      const exhaustive: never = el;
      throw new Error(`알 수 없는 요소: ${JSON.stringify(exhaustive)}`);
    }
  }
}

export function orderByZ(elements: Element[]): Element[] {
  // z 오름차순으로 그리면 큰 z 가 위로 온다. 같은 z 는 입력 순서를 지킨다(안정 정렬).
  return elements
    .map((el, i) => ({ el, i }))
    .sort((a, b) => a.el.z - b.el.z || a.i - b.i)
    .map((x) => x.el);
}

export function renderSlide(sink: SlideSink, slide: Slide, resolveChart: ResolveChart): void {
  for (const el of orderByZ(slide.elements)) {
    placeElement(sink, el, resolveChart);
  }
}

// 진짜 pptxgen 에 붙여 .pptx 를 만든다. 여기만 pptxgen 타입에 의존한다.
export function buildPptx(deck: Deck, resolveChart: ResolveChart): pptxgen {
  const pptx = new pptxgen();
  pptx.defineLayout({ name: "IR", width: deck.width, height: deck.height });
  pptx.layout = "IR";

  for (const slide of deck.slides) {
    const target = pptx.addSlide();
    const sink: SlideSink = {
      addText: (text, opts) => {
        target.addText(text, opts as pptxgen.TextPropsOptions);
      },
      addImage: (opts) => {
        target.addImage(opts as pptxgen.ImageProps);
      },
      addShape: (shape, opts) => {
        target.addShape(shape as pptxgen.ShapeType, opts as pptxgen.ShapeProps);
      },
    };
    renderSlide(sink, slide, resolveChart);
  }
  return pptx;
}
