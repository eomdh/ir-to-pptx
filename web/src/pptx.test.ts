import { describe, expect, it, vi } from "vitest";
import type { Element } from "./ir";
import { orderByZ, placeElement, renderSlide, type SlideSink } from "./pptx";

type Call = { m: string; args: unknown[] };

// 실제 pptxgen 을 띄우지 않고, 어떤 호출이 어떤 인자로 갔는지만 기록하는 가짜 sink.
function fakeSink() {
  const calls: Call[] = [];
  const sink: SlideSink = {
    addText: (...args) => calls.push({ m: "addText", args }),
    addImage: (...args) => calls.push({ m: "addImage", args }),
    addShape: (...args) => calls.push({ m: "addShape", args }),
  };
  return { sink, calls };
}

function firstCall(calls: Call[]): Call {
  const c = calls[0];
  if (!c) throw new Error("기록된 호출이 없다");
  return c;
}

const box = { x: 1, y: 2, w: 3, h: 0.5, z: 0 };

describe("placeElement", () => {
  it("text 요소는 좌표·폰트·불릿을 그대로 실어 addText 한다", () => {
    const { sink, calls } = fakeSink();
    placeElement(
      sink,
      {
        type: "text",
        ...box,
        text: "매출 증가",
        runs: null,
        size: 16,
        bold: false,
        italic: false,
        color: "1A1A1A",
        align: "left",
        bullet: true,
      },
      () => "",
    );
    const call = firstCall(calls);
    expect(call.m).toBe("addText");
    const [text, opts] = call.args as [string, Record<string, unknown>];
    expect(text).toBe("매출 증가");
    // 인치 좌표는 변환 없이 통과한다.
    expect(opts).toMatchObject({
      x: 1,
      y: 2,
      w: 3,
      h: 0.5,
      fontSize: 16,
      color: "1A1A1A",
      align: "left",
      bullet: true,
    });
  });

  it("runs 가 있으면 조각별 강조를 실은 배열로 addText 한다", () => {
    const { sink, calls } = fakeSink();
    placeElement(
      sink,
      {
        type: "text",
        ...box,
        text: "보통 굵게",
        runs: [
          { text: "보통 ", bold: false, italic: false },
          { text: "굵게", bold: true, italic: false },
        ],
        size: 16,
        bold: false,
        italic: false,
        color: "1A1A1A",
        align: "left",
        bullet: false,
      },
      () => "",
    );
    const [text] = firstCall(calls).args as [unknown, Record<string, unknown>];
    // 평문 문자열이 아니라 조각 배열이 넘어간다. 강조는 조각의 options 에 실린다.
    expect(text).toEqual([
      { text: "보통 ", options: { bold: false, italic: false } },
      { text: "굵게", options: { bold: true, italic: false } },
    ]);
  });

  it("shape 요소는 addShape(rect, fill) 로 간다", () => {
    const { sink, calls } = fakeSink();
    placeElement(sink, { type: "shape", ...box, shape: "rect", fill: "2563EB" }, () => "");
    const call = firstCall(calls);
    expect(call.m).toBe("addShape");
    const [shape, opts] = call.args as [string, Record<string, unknown>];
    expect(shape).toBe("rect");
    expect(opts).toMatchObject({ x: 1, y: 2, fill: { color: "2563EB" } });
  });

  it("URL 이미지는 path, data URI 이미지는 data 로 넣는다", () => {
    const url = fakeSink();
    placeElement(url.sink, { type: "image", ...box, src: "https://x/y.png" }, () => "");
    expect((firstCall(url.calls).args[0] as Record<string, unknown>).path).toBe("https://x/y.png");

    const dataUri = fakeSink();
    placeElement(
      dataUri.sink,
      { type: "image", ...box, src: "data:image/png;base64,AAAA" },
      () => "",
    );
    expect((firstCall(dataUri.calls).args[0] as Record<string, unknown>).data).toBe(
      "data:image/png;base64,AAAA",
    );
  });

  it("chart 요소는 리졸버가 만든 PNG 를 그 자리에 이미지로 얹는다", () => {
    const { sink, calls } = fakeSink();
    const resolve = vi.fn(() => "data:image/png;base64,CHART");
    placeElement(
      sink,
      {
        type: "chart",
        ...box,
        spec: { kind: "bar", categories: ["A"], series: [{ name: "s", data: [1] }] },
      },
      resolve,
    );
    expect(resolve).toHaveBeenCalledOnce();
    const call = firstCall(calls);
    expect(call.m).toBe("addImage");
    expect(call.args[0] as Record<string, unknown>).toMatchObject({
      x: 1,
      y: 2,
      data: "data:image/png;base64,CHART",
    });
  });
});

describe("orderByZ", () => {
  it("z 오름차순으로 정렬하고 같은 z 는 원래 순서를 지킨다(안정)", () => {
    const els: Element[] = [
      {
        type: "text",
        x: 0,
        y: 0,
        w: 1,
        h: 1,
        z: 2,
        text: "위",
        runs: null,
        size: 12,
        bold: false,
        italic: false,
        color: "000000",
        align: "left",
        bullet: false,
      },
      { type: "shape", x: 0, y: 0, w: 1, h: 1, z: 0, shape: "rect", fill: "EEEEEE" },
      {
        type: "text",
        x: 0,
        y: 0,
        w: 1,
        h: 1,
        z: 0,
        text: "배경옆",
        runs: null,
        size: 12,
        bold: false,
        italic: false,
        color: "000000",
        align: "left",
        bullet: false,
      },
    ];
    const ordered = orderByZ(els);
    expect(ordered.map((e) => e.z)).toEqual([0, 0, 2]);
    // 같은 z(0) 안에서는 입력 순서(shape 먼저) 유지
    expect(ordered.map((e) => e.type)).toEqual(["shape", "text", "text"]);
  });
});

describe("renderSlide", () => {
  it("한 슬라이드의 요소를 z 순서대로 그린다(뒤 요소가 위로)", () => {
    const { sink, calls } = fakeSink();
    renderSlide(
      sink,
      {
        elements: [
          {
            type: "text",
            x: 0,
            y: 0,
            w: 1,
            h: 1,
            z: 1,
            text: "제목",
            runs: null,
            size: 20,
            bold: true,
            italic: false,
            color: "000000",
            align: "left",
            bullet: false,
          },
          { type: "shape", x: 0, y: 0, w: 1, h: 1, z: 0, shape: "rect", fill: "2563EB" },
        ],
      },
      () => "",
    );
    // z=0 shape 가 먼저(아래), z=1 text 가 나중(위)
    expect(calls.map((c) => c.m)).toEqual(["addShape", "addText"]);
  });
});
