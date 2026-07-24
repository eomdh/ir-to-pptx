// DOM 미리보기. .pptx 와 똑같은 IR 을 받아 절대좌표 div 로 그린다.
// 좌표 계산이 여기 없다는 게 핵심이다. pptx.ts 와 이 파일은 같은 IR 을 서로
// 다른 표면에 배치할 뿐이라, 화면과 파일이 같아진다.

import { type CSSProperties, useMemo } from "react";
import { renderChartPng } from "./chart";
import type { ChartElement, Deck, Element, Slide } from "./ir";

// 인치당 픽셀. 72 로 두면 pt(폰트) 와 px 가 1:1 이라 크기 환산이 없다.
const PX = 72;

function box(el: Element): CSSProperties {
  return {
    position: "absolute",
    left: el.x * PX,
    top: el.y * PX,
    width: el.w * PX,
    height: el.h * PX,
    zIndex: el.z,
  };
}

function ChartView({ el }: { el: ChartElement }) {
  const png = useMemo(
    () => renderChartPng(el.spec, el.w * PX * 2, el.h * PX * 2),
    [el.spec, el.w, el.h],
  );
  return (
    <img src={png} alt="차트" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
  );
}

function ElementView({ el }: { el: Element }) {
  switch (el.type) {
    case "text":
      return (
        <div
          style={{
            ...box(el),
            fontSize: el.size,
            fontWeight: el.bold ? 700 : 400,
            color: `#${el.color}`,
            textAlign: el.align,
            lineHeight: 1.25,
            whiteSpace: "pre-wrap",
            overflow: "hidden",
          }}
        >
          {el.bullet ? `• ${el.text}` : el.text}
        </div>
      );
    case "shape":
      return <div style={{ ...box(el), background: `#${el.fill}` }} />;
    case "image":
      return <img src={el.src} alt="" style={{ ...box(el), objectFit: "contain" }} />;
    case "chart":
      return (
        <div style={box(el)}>
          <ChartView el={el} />
        </div>
      );
    default: {
      const exhaustive: never = el;
      throw new Error(`알 수 없는 요소: ${JSON.stringify(exhaustive)}`);
    }
  }
}

function elementKey(el: Element): string {
  return `${el.type}@${el.x},${el.y},${el.z}`;
}

export function SlidePreview({ slide, deck }: { slide: Slide; deck: Deck }) {
  return (
    <div
      style={{
        position: "relative",
        width: deck.width * PX,
        height: deck.height * PX,
        background: "#fff",
        borderRadius: 8,
        boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
        border: "1px solid #E5E7EB",
        flex: "none",
      }}
    >
      {slide.elements.map((el) => (
        <ElementView key={elementKey(el)} el={el} />
      ))}
    </div>
  );
}
