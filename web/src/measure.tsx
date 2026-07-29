// 레이아웃 엔진의 줄 수 예측이 실제 렌더와 얼마나 어긋나는지 재는 하네스.
//
// 엔진(metrics.line_count)은 글상자 폭에서 텍스트가 몇 줄로 접힐지 세어 블록 높이를
// 잡는다. 그 예측이 맞는지는 진짜 텍스트 레이아웃 엔진만 안다. 그래서 미리보기
// 컴포넌트를 그대로 렌더한 뒤, 각 글상자를 복제해 높이 제한만 풀고 실제 몇 줄이
// 되는지 잰다. 복제본은 인라인 스타일을 그대로 물려받으므로 스타일을 여기서
// 흉내낼 필요가 없다. 재는 대상이 화면에 실제로 나가는 그 상자다.
//
// 어긋남은 두 방향이고 무게가 다르다.
//   과소 예측: 실제가 예측보다 길다. 글이 예산 밖으로 나가 다음 블록과 겹친다.
//   과대 예측: 실제가 예측보다 짧다. 안 겹치지만 빈 자리가 남아 슬라이드가 헐거워진다.
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

// layout.py 의 값과 같아야 한다. 엔진은 높이를 줄수 × 줄높이 로 잡으므로
// IR 의 h 를 이 값으로 나누면 엔진이 예측한 줄 수가 되돌아 나온다.
const BULLET_LINE_H = 0.42;
const PARA_LINE_H = 0.4;

// 줄 수로 높이를 잡는 블록은 불릿과 문단뿐이고, 둘 다 16pt 다(layout.py 의
// BULLET_SIZE, PARA_SIZE). 제목 28, 소제목 18, 표 13, KPI 24/12 는 고정 높이라 뺀다.
const LINE_SIZED_PT = 16;

interface Row {
  text: string;
  bullet: boolean;
  predicted: number;
  actual: number;
}

interface Summary {
  total: number;
  wrong: number;
  under: number; // 실제 > 예측, 겹침 위험
  over: number; // 실제 < 예측, 빈 자리
  wrongLines: number;
}

function predictedLines(el: TextElement): number {
  return Math.round(el.h / (el.bullet ? BULLET_LINE_H : PARA_LINE_H));
}

function summarize(rows: Row[]): Summary {
  let under = 0;
  let over = 0;
  let wrongLines = 0;
  for (const r of rows) {
    const diff = r.actual - r.predicted;
    if (diff > 0) under += 1;
    else if (diff < 0) over += 1;
    wrongLines += Math.abs(diff);
  }
  return { total: rows.length, wrong: under + over, under, over, wrongLines };
}

/** 글상자를 복제해 높이 제한만 풀고, 실제로 몇 줄이 되는지 잰다. */
function measureLines(box: HTMLElement): number {
  const clone = box.cloneNode(true) as HTMLElement;
  clone.style.position = "absolute";
  clone.style.visibility = "hidden";
  clone.style.height = "auto";
  clone.style.overflow = "visible";
  document.body.appendChild(clone);
  const lineHeight = Number.parseFloat(getComputedStyle(clone).lineHeight);
  const lines = Math.round(clone.getBoundingClientRect().height / lineHeight);
  clone.remove();
  return lines;
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
          measured.push({
            text: el.text,
            bullet: el.bullet,
            predicted: predictedLines(el),
            actual: measureLines(box),
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
      <h1 className="mb-4 text-base font-semibold">줄 수 예측 대 실제</h1>

      {s ? (
        <table className="mb-6 border-collapse">
          <tbody>
            {[
              ["대상 요소", `${s.total}개 (16pt 불릿과 문단)`],
              ["어긋난 요소", `${s.wrong}개 (${((s.wrong / s.total) * 100).toFixed(1)}%)`],
              ["과소 예측", `${s.under}개 (겹침 위험)`],
              ["과대 예측", `${s.over}개 (빈 자리)`],
              ["총 어긋난 줄", `${s.wrongLines}줄`],
            ].map(([k, v]) => (
              <tr key={k}>
                <td className="border border-neutral-200 px-3 py-1 text-neutral-500">{k}</td>
                <td className="border border-neutral-200 px-3 py-1 font-semibold">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mb-6 text-neutral-400">재는 중</p>
      )}

      {wrong.length > 0 && (
        <>
          <h2 className="mb-2 font-semibold">어긋난 요소</h2>
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
