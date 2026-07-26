import { Download, Presentation } from "lucide-react";
import { useEffect, useState } from "react";
import { loadECharts, renderChartPng } from "./chart";
import type { Deck } from "./ir";
import type { ResolveChart } from "./pptx";
import { SlidePreview } from "./SlidePreview";
import { SAMPLE_MARKDOWN } from "./sample";

export default function App() {
  const [markdown, setMarkdown] = useState(SAMPLE_MARKDOWN);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 마크다운이 멈추면(350ms) 서버에 IR 을 다시 청한다. 늦게 온 응답이
  // 최신 입력을 덮지 않도록 cancelled 로 막는다.
  useEffect(() => {
    let cancelled = false;
    const id = setTimeout(async () => {
      try {
        const res = await fetch("/ir", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ markdown }),
        });
        if (cancelled) return;
        if (!res.ok) {
          setError(`서버 오류 ${res.status}`);
          return;
        }
        setDeck(await res.json());
        setError(null);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [markdown]);

  async function download() {
    if (!deck) return;
    // 무거운 두 의존성(pptxgenjs, echarts)을 이때 처음 불러온다. 초기 로딩에는 빠져 있다.
    const [{ buildPptx }, echarts] = await Promise.all([import("./pptx"), loadECharts()]);
    // 미리보기와 같은 renderChartPng 로 그림을 만든다. 다운로드는 더 큰 해상도로.
    const resolveChart: ResolveChart = (el) =>
      renderChartPng(echarts, el.spec, el.w * 96 * 2, el.h * 96 * 2);
    buildPptx(deck, resolveChart).writeFile({ fileName: "ir-to-pptx.pptx" });
  }

  const slideCount = deck?.slides.length ?? 0;

  return (
    <div className="flex h-screen flex-col bg-neutral-50 text-neutral-900">
      <header className="flex h-14 items-center gap-2 border-b border-neutral-200 bg-white px-5">
        <Presentation className="text-[#3182F6]" size={20} />
        <span className="font-mono text-base font-semibold">ir-to-pptx</span>
        <span className="ml-2 text-sm text-neutral-400">마크다운 → 평면 IR → 브라우저 PPTX</span>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-2">
        <section className="flex min-h-0 flex-col border-r border-neutral-200 bg-white">
          <div className="border-b border-neutral-100 px-5 py-2 text-xs font-medium text-neutral-400">
            마크다운
          </div>
          <textarea
            className="min-h-0 flex-1 resize-none p-5 font-mono text-sm leading-relaxed outline-none"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            spellCheck={false}
          />
        </section>

        <section className="flex min-h-0 flex-col">
          <div className="flex h-11 items-center justify-between border-b border-neutral-200 bg-white px-5">
            <span className="text-sm text-neutral-500">슬라이드 {slideCount}장</span>
            <button
              type="button"
              onClick={download}
              disabled={!deck}
              className="flex h-9 items-center gap-2 rounded-xl bg-[#3182F6] px-4 text-sm font-medium text-white transition-colors hover:bg-[#2b74e0] disabled:opacity-40"
            >
              <Download size={16} />
              PPTX 다운로드
            </button>
          </div>

          {error && (
            <div className="border-b border-red-100 bg-red-50 px-5 py-2 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="flex min-h-0 flex-1 flex-col items-start gap-6 overflow-auto p-6">
            {deck?.slides.map((slide, i) => (
              <SlidePreview key={`slide-${slideSignature(slide, i)}`} slide={slide} deck={deck} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function slideSignature(slide: Deck["slides"][number], index: number): string {
  const first = slide.elements[0];
  const head = first ? `${first.type}${first.x},${first.y}` : "empty";
  return `${index}-${head}-${slide.elements.length}`;
}
