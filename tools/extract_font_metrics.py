"""Pretendard 에서 글자 폭을 뽑아 `src/ir_pptx/font_metrics.py` 를 만든다.

    uv run --group tools python tools/extract_font_metrics.py

왜 런타임에 폰트를 읽지 않고 표를 구워서 커밋하나.

  1. 결정성 — 레이아웃 엔진이 "같은 마크다운은 항상 같은 IR" 이어야 하는데, 런타임에
     폰트 파일을 파싱하면 파일 유무와 버전에 결과가 딸려간다.
  2. 의존성 — 서버가 폰트를 안 읽으므로 fontTools 가 런타임 의존성이 아니다. CI 도
     폰트 파일 없이 돈다.

표를 다시 구워야 할 때는 폰트를 바꿀 때뿐이고, 그때는 이 스크립트를 돌려 생성물을
같이 커밋한다.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "web/public/fonts/Pretendard-Regular.woff2"
OUT_PATH = ROOT / "src/ir_pptx/font_metrics.py"

# 한 폭으로 통일된 구간. 글자마다 적지 않고 구간 하나로 접는다.
# (범위, 이름) 만 적고 폭이 정말 하나인지는 아래에서 확인한다.
UNIFORM = [
    (0xAC00, 0xD7A3, "한글 음절"),
    (0x3130, 0x318F, "한글 호환 자모"),
    (0x3040, 0x30FF, "히라가나, 가타카나"),
    (0xFF00, 0xFF60, "전각 기호"),
]

# 글자마다 폭이 다른 구간. 실제 문서에 나오는 것만 담는다. 여기 없는 글자는
# 폴백으로 떨어지고, 폴백은 넉넉한 쪽이라 줄 수를 적게 잡지 않는다.
PER_CHAR = [
    (0x20, 0x7E, "ASCII"),
    (0xA0, 0xFF, "라틴 1 보충"),
    (0x2000, 0x206F, "일반 문장부호"),
    (0x20A0, 0x20BF, "통화 기호"),
    (0x2100, 0x214F, "글자꼴 기호"),
    (0x2190, 0x21FF, "화살표"),
    (0x2200, 0x22FF, "수학 연산자"),
    (0x25A0, 0x25FF, "도형"),
    (0x2600, 0x27BF, "기타 기호, 딩벳"),
    (0x3000, 0x303F, "CJK 문장부호"),
]

# 폰트에 없는 글자의 폭. 브라우저가 다른 폰트로 대신 그리므로 알 수 없고,
# 이 모듈의 원칙(줄 수를 적게 잡지 않는다)에 따라 넉넉한 쪽인 전각으로 둔다.
# 대표적으로 한자(U+4E00~U+9FFF)가 여기로 온다. Pretendard 에는 한자가 없다.
FALLBACK = 1.0


def main() -> None:
    font = TTFont(FONT_PATH)
    upm = font["head"].unitsPerEm
    hmtx, cmap = font["hmtx"], font.getBestCmap()

    def width(code: int) -> float | None:
        glyph = cmap.get(code)
        return round(hmtx[glyph][0] / upm, 4) if glyph else None

    uniform_rows = []
    for lo, hi, name in UNIFORM:
        found = [w for c in range(lo, hi + 1) if (w := width(c)) is not None]
        # 0 폭(조합용 빈 글자)은 대표값 판단에서 뺀다.
        real = set(found) - {0.0}
        if len(real) != 1:
            raise SystemExit(f"{name} 구간의 폭이 하나가 아니다: {sorted(real)[:5]}")
        uniform_rows.append((lo, hi, real.pop(), name, len(found)))

    per_char: dict[int, float] = {}
    covered = []
    for lo, hi, name in PER_CHAR:
        got = {c: w for c in range(lo, hi + 1) if (w := width(c)) is not None}
        per_char.update(got)
        covered.append((name, len(got), hi - lo + 1))

    OUT_PATH.write_text(render(uniform_rows, per_char, covered), encoding="utf-8")
    print(f"{OUT_PATH.relative_to(ROOT)} 생성")
    print(f"  구간 {len(uniform_rows)}개, 글자 {len(per_char)}개")


def render(uniform_rows, per_char: dict[int, float], covered) -> str:
    head = [
        '"""Pretendard 글자 폭 표. 생성물이라 직접 고치지 않는다.',
        "",
        "    uv run --group tools python tools/extract_font_metrics.py",
        "",
        "값은 em 비율이다. 글자 높이가 1em 일 때의 가로 advance 이므로, 실제 폭은",
        "값 × 글자크기(pt) ÷ 72 인치가 된다. 폰트를 바꾸면 이 표도 같이 다시 굽는다.",
        "",
        "담은 범위:",
    ]
    for name, got, total in covered:
        head.append(f"  {name} {got}/{total}자")
    head += [
        "",
        "굵기는 보지 않는다. 한글은 Regular 와 Bold 의 폭이 같고(0.8643), 라틴만",
        "평균 7% 넓어진다. 그래서 강조가 많은 라틴 문장에서만 어긋날 수 있다.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        'FONT_NAME = "Pretendard"',
        f"FALLBACK_EM = {FALLBACK}",
        "",
        "# (시작, 끝, 폭). 구간 안 글자는 폭이 전부 같아 하나로 접었다.",
        "UNIFORM_RANGES: tuple[tuple[int, int, float], ...] = (",
    ]
    for lo, hi, w, name, n in uniform_rows:
        head.append(f"    (0x{lo:04X}, 0x{hi:04X}, {w}),  # {name} {n}자")
    head += [
        ")",
        "",
        "# 글자마다 폭이 다른 구간. 키는 코드포인트.",
        "CHAR_EM: dict[int, float] = {",
    ]
    for code in sorted(per_char):
        ch = chr(code)
        label = repr(ch) if ch.isprintable() and ch != " " else f"U+{code:04X}"
        head.append(f"    0x{code:04X}: {per_char[code]},  # {label}")
    head += ["}", ""]
    return "\n".join(head)


if __name__ == "__main__":
    main()
