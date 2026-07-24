// 차트 요소를 실제 그림으로 바꾸는 곳. 백엔드는 위치와 spec 만 줬고, 여기서
// ECharts 로 그려 PNG(data URI)로 캡처한다. 원본의 isChartCapture 패턴이다.
//
// 미리보기와 .pptx 가 "같은 그림"을 쓰도록, 둘 다 이 함수가 낸 PNG 를 얹는다.

import * as echarts from "echarts";
import type { ChartSpec } from "./ir";

// toss 계열 팔레트.
const PALETTE = ["#3182F6", "#00C2A8", "#F5A623", "#8B5CF6", "#F04452"];

export function toEChartsOption(spec: ChartSpec): echarts.EChartsOption {
  const base: echarts.EChartsOption = {
    // 동기 캡처를 위해 애니메이션을 끈다. 켜져 있으면 setOption 직후 프레임이
    // 비어 getDataURL 이 빈 그림을 낸다.
    animation: false,
    color: PALETTE,
    textStyle: { fontFamily: "sans-serif" },
    title: spec.title
      ? { text: spec.title, left: "center", textStyle: { fontSize: 14 } }
      : undefined,
  };

  if (spec.kind === "pie") {
    const first = spec.series[0];
    return {
      ...base,
      series: [
        {
          type: "pie",
          radius: "62%",
          data: spec.categories.map((name, i) => ({ name, value: first?.data[i] ?? 0 })),
        },
      ],
    };
  }

  return {
    ...base,
    grid: {
      left: 44,
      right: 20,
      top: spec.title ? 44 : 20,
      bottom: spec.series.length > 1 ? 44 : 28,
    },
    legend: spec.series.length > 1 ? { bottom: 0 } : undefined,
    xAxis: { type: "category", data: spec.categories },
    yAxis: { type: "value" },
    series: spec.series.map((s) => ({
      name: s.name,
      type: spec.kind,
      data: s.data,
    })) as echarts.SeriesOption[],
  };
}

// 화면 밖 컨테이너에 그려 PNG 로 뽑고 정리한다.
export function renderChartPng(spec: ChartSpec, widthPx: number, heightPx: number): string {
  const host = document.createElement("div");
  host.style.cssText = `position:absolute;left:-99999px;top:0;width:${widthPx}px;height:${heightPx}px`;
  document.body.appendChild(host);

  const chart = echarts.init(host, undefined, { renderer: "canvas" });
  chart.setOption(toEChartsOption(spec));
  const uri = chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#ffffff" });

  chart.dispose();
  host.remove();
  return uri;
}
