// 레이아웃 엔진이 잡은 글상자가 실제 렌더와 얼마나 맞는지 재는 하네스.
//
// 미리보기 컴포넌트를 그대로 렌더한 뒤, 각 글상자를 복제해 높이 제한만 풀고 실제
// 크기를 잰다. 복제본은 인라인 스타일을 그대로 물려받으므로 스타일을 여기서
// 흉내낼 필요가 없다. 재는 대상이 화면에 실제로 나가는 그 상자다.
//
// 두 가지를 본다.
//
//   줄 수: 엔진이 몇 줄로 접힐지 맞혔나. 틀리면 그만큼 자리가 어긋난다.
//   남는 자리: 상자 높이에서 글 높이를 뺀 값. 글상자는 위쪽 정렬이라 남는 자리는
//     전부 아래에 깔리고, 그게 곧 다음 블록과의 간격이 된다. 그래서 0 이 이상적인
//     게 아니라 "줄 수와 무관하게 일정한 것" 이 이상적이다. 한 줄 불릿 뒤와 세 줄
//     불릿 뒤의 간격이 다르면 세로 리듬이 들쭉날쭉해진다.
//
// dev 전용이다. vite build 는 index.html 만 엔트리로 잡으므로 배포 산출물에 안 들어간다.
//
//   uv run uvicorn ir_pptx.main:app --port 8000    # 다른 창에서
//   pnpm --dir web dev
//   http://localhost:5173/measure.html

import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import type { Deck, TextElement } from "./ir";
import { PROBE_MARKDOWN } from "./probes";
import { SlidePreview } from "./SlidePreview";

// SlidePreview 와 같은 인치당 픽셀.
const PX = 72;

// layout.py 의 높이 공식을 되짚기 위한 값. 엔진이 h 를 어떻게 잡는지 알아야
// 거기서 "엔진이 예측한 줄 수" 를 되돌릴 수 있다. layout.py 를 고치면 여기도 고친다.
const BULLET_LINE_H = 0.42;
const PARA_LINE_H = 0.4;
const BULLET_GAP = 0;
const PARA_GAP = 0;

// 줄 수로 높이를 잡는 블록은 불릿과 문단뿐이고, 둘 다 16pt 다(layout.py 의
// BULLET_SIZE, PARA_SIZE). 제목 28, 소제목 18, 표 13, KPI 24/12 는 고정 높이라 뺀다.
const LINE_SIZED_PT = 16;

interface Row {
  text: string;
  bullet: boolean;
  predicted: number;
  actual: number;
  budgetIn: number;
  contentIn: number;
}

interface SlackByLines {
  lines: number;
  count: number;
  slackIn: number;
}

interface Summary {
  total: number;
  wrong: number;
  under: number; // 실제 > 예측, 겹침 위험
  over: number; // 실제 < 예측, 빈 자리
  wrongLines: number;
  overflowed: number; // 남는 자리가 음수, 글이 상자 밖으로
  slackByLines: SlackByLines[];
  slackSpreadIn: number; // 줄 수별 남는 자리의 최대와 최소 차이
}

function predictedLines(el: TextElement): number {
  const [lineH, gap] = el.bullet ? [BULLET_LINE_H, BULLET_GAP] : [PARA_LINE_H, PARA_GAP];
  return Math.round((el.h - gap) / lineH);
}

function summarize(rows: Row[]): Summary {
  let under = 0;
  let over = 0;
  let wrongLines = 0;
  let overflowed = 0;
  const buckets = new Map<number, number[]>();

  for (const r of rows) {
    const diff = r.actual - r.predicted;
    if (diff > 0) under += 1;
    else if (diff < 0) over += 1;
    wrongLines += Math.abs(diff);

    const slack = r.budgetIn - r.contentIn;
    if (slack < -0.001) overflowed += 1;
    const bucket = buckets.get(r.actual) ?? [];
    bucket.push(slack);
    buckets.set(r.actual, bucket);
  }

  const slackByLines = [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([lines, slacks]) => ({
      lines,
      count: slacks.length,
      slackIn: slacks.reduce((a, b) => a + b, 0) / slacks.length,
    }));
  const averages = slackByLines.map((s) => s.slackIn);

  return {
    total: rows.length,
    wrong: under + over,
    under,
    over,
    wrongLines,
    overflowed,
    slackByLines,
    slackSpreadIn: averages.length ? Math.max(...averages) - Math.min(...averages) : 0,
  };
}

/** 글상자를 복제해 높이 제한만 풀고, 실제 줄 수와 글 높이를 잰다. */
function measureBox(box: HTMLElement): { lines: number; contentIn: number } {
  const clone = box.cloneNode(true) as HTMLElement;
  clone.style.position = "absolute";
  clone.style.visibility = "hidden";
  clone.style.height = "auto";
  clone.style.overflow = "visible";
  document.body.appendChild(clone);
  const lineHeight = Number.parseFloat(getComputedStyle(clone).lineHeight);
  const height = clone.getBoundingClientRect().height;
  clone.remove();
  return { lines: Math.round(height / lineHeight), contentIn: height / PX };
}

function Report({ deck }: { deck: Deck }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [rows, setRows] = useState<Row[] | null>(null);

  useEffect(() => {
    let alive = true;
    // 폰트가 붙기 전에 재면 폴백 폰트를 재게 된다. 그 뒤 타이머로 한 번 더 미루는 건
    // 리액트가 DOM 을 커밋할 틈을 주려는 것. rAF 는 탭이 안 보이면 안 돌아서 안 쓴다.
    document.fonts.ready.then(() =>
      setTimeout(() => {
        const host = hostRef.current;
        if (!alive || !host) return;
        // DOM 순서와 IR 순서가 같다(SlidePreview 가 elements 를 그 순서로 그린다).
        const boxes = Array.from(host.querySelectorAll<HTMLElement>("[data-text-el]"));
        const all = deck.slides.flatMap((s) => s.elements.filter((el) => el.type === "text"));
        const measured: Row[] = [];
        all.forEach((el, i) => {
          const box = boxes[i];
          if (!box || el.size !== LINE_SIZED_PT) return;
          const { lines, contentIn } = measureBox(box);
          measured.push({
            text: el.text,
            bullet: el.bullet,
            predicted: predictedLines(el),
            actual: lines,
            budgetIn: el.h,
            contentIn,
          });
        });
        setRows(measured);
      }, 150),
    );
    return () => {
      alive = false;
    };
  }, [deck]);

  const s = rows ? summarize(rows) : null;
  const wrong = rows ? rows.filter((r) => r.actual !== r.predicted) : [];
  // 인덱스를 키로 직접 쓰지 않도록 미리 뽑아 둔다.
  const slides = deck.slides.map((slide, i) => ({ key: `slide-${i}`, slide }));

  return (
    <div className="p-6 text-sm">
      <h1 className="mb-4 text-base font-semibold">글상자 예측 대 실제</h1>

      {s ? (
        <>
          <table className="mb-6 border-collapse">
            <tbody>
              {[
                ["대상 글상자", `${s.total}개 (16pt 불릿과 문단)`],
                ["줄 수 어긋남", `${s.wrong}개 (${((s.wrong / s.total) * 100).toFixed(1)}%)`],
                ["과소 예측", `${s.under}개 (겹침 위험)`],
                ["넘친 상자", `${s.overflowed}개 (글이 상자 밖으로)`],
                ["남는 자리 편차", `${s.slackSpreadIn.toFixed(3)}in (줄 수별 평균의 최대 최소 차)`],
              ].map(([k, v]) => (
                <tr key={k}>
                  <td className="border border-neutral-200 px-3 py-1 text-neutral-500">{k}</td>
                  <td className="border border-neutral-200 px-3 py-1 font-semibold">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 className="mb-2 font-semibold">줄 수별 남는 자리</h2>
          <p className="mb-2 text-neutral-500">
            상자 높이에서 글 높이를 뺀 값. 위쪽 정렬이라 전부 아래에 깔려 다음 블록과의 간격이 된다.
            줄 수가 늘어도 일정해야 세로 리듬이 고르다.
          </p>
          <table className="mb-6 border-collapse">
            <tbody>
              <tr>
                {s.slackByLines.map((b) => (
                  <td
                    key={b.lines}
                    className="border border-neutral-200 px-3 py-1 text-neutral-500"
                  >
                    {b.lines}줄 ({b.count}개)
                  </td>
                ))}
              </tr>
              <tr>
                {s.slackByLines.map((b) => (
                  <td
                    key={b.lines}
                    className={`border border-neutral-200 px-3 py-1 font-semibold ${
                      b.slackIn < 0 ? "text-red-600" : ""
                    }`}
                  >
                    {b.slackIn.toFixed(3)}in
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </>
      ) : (
        <p className="mb-6 text-neutral-400">재는 중</p>
      )}

      {wrong.length > 0 && (
        <>
          <h2 className="mb-2 font-semibold">줄 수가 어긋난 상자</h2>
          <ul className="mb-6 space-y-1">
            {wrong.map((r) => (
              <li key={`${r.text}:${r.predicted}`} className="text-neutral-600">
                <span
                  className={
                    r.actual > r.predicted ? "font-semibold text-red-600" : "text-amber-600"
                  }
                >
                  예측 {r.predicted}줄, 실제 {r.actual}줄
                </span>{" "}
                <span className="text-neutral-400">{r.bullet ? "불릿" : "문단"}</span>{" "}
                {r.text.slice(0, 70)}
              </li>
            ))}
          </ul>
        </>
      )}

      {/* 재는 대상. 화면에 나가는 그 컴포넌트를 그대로 렌더한다. */}
      <div ref={hostRef} className="flex flex-col items-start gap-6">
        {slides.map(({ key, slide }) => (
          <SlidePreview key={key} slide={slide} deck={deck} />
        ))}
      </div>
    </div>
  );
}

function Measure() {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/ir", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ markdown: PROBE_MARKDOWN }),
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`서버 오류 ${res.status}`))))
      .then(setDeck)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="p-6 text-red-600">{error} (백엔드가 떠 있는지 확인)</p>;
  if (!deck) return <p className="p-6 text-neutral-400">IR 받는 중</p>;
  return <Report deck={deck} />;
}

const root = document.getElementById("root");
if (root) {
  // StrictMode 이중 렌더는 측정 타이밍만 흔든다. 하네스라 뺀다.
  createRoot(root).render(<Measure />);
}

export type { Row };
export { predictedLines, summarize };
