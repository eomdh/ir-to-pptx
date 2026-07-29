"""텍스트 줄 수 계산.

한 글상자에서 텍스트가 몇 줄로 접히는지 센다. 레이아웃(`layout.py`)이 이 값으로
불릿과 문단의 세로 높이를 잡는다.

글자 폭은 Pretendard 에서 실제로 뽑은 표(`font_metrics.py`)를 쓴다. 표가 의미를
가지려면 렌더러도 같은 폰트를 써야 하고, 그래서 미리보기(`web/src/index.css`)와
.pptx(`web/src/pptx.ts` 의 FONT_FACE)가 같은 폰트로 묶여 있다. 셋 중 하나만 달라도
여기서 센 줄 수는 화면에서 안 맞는다.

지키는 것 둘.

  1. 결정성 — 같은 입력은 항상 같은 줄 수. 미리보기와 pptx 파일이 같은 IR 을
     받는다는 전제의 뿌리. 표를 커밋해 두는 것도 이 때문이다(런타임에 폰트를
     파싱하면 파일 유무와 버전에 결과가 딸려간다).
  2. 과소 계산 금지 — 줄 수를 실제보다 적게 잡으면 글상자가 촘촘해져 다음 블록과
     겹친다. 표에 없는 글자를 전각(1em)으로 치는 것도 오차를 위쪽으로만 두려는 것.

굵기는 안 본다. 한글은 Regular 와 Bold 의 폭이 같아서 영향이 없고, 라틴만 평균
7% 넓어진다. 강조가 많은 라틴 문장에서만 어긋난다.
"""

from __future__ import annotations

from ir_pptx.font_metrics import CHAR_EM, FALLBACK_EM, UNIFORM_RANGES


def _is_cjk(o: int) -> bool:
    """줄바꿈이 글자 단위로 되는 전각 문자인가.

    폭이 아니라 **줄바꿈 규칙**을 가르는 판정이다. 전각은 어디서든 끊을 수 있고
    라틴 덩이는 중간에서 못 끊는다. 폭은 이것과 무관하게 표에서 가져온다.
    """
    return (
        0xAC00 <= o <= 0xD7A3  # 한글 음절
        or 0x1100 <= o <= 0x11FF  # 한글 자모
        or 0x3130 <= o <= 0x318F  # 한글 호환 자모
        or 0x3040 <= o <= 0x30FF  # 히라가나, 가타카나
        or 0x4E00 <= o <= 0x9FFF  # CJK 한자
        or 0xFF00 <= o <= 0xFF60  # 전각 기호
    )


def char_em(o: int) -> float:
    """글자 하나의 가로 폭(em). 표에 없으면 넉넉한 쪽인 전각으로 친다."""
    width = CHAR_EM.get(o)
    if width is not None:
        return width
    for lo, hi, uniform in UNIFORM_RANGES:
        if lo <= o <= hi:
            return uniform
    return FALLBACK_EM


def text_width(text: str, size_pt: float) -> float:
    """한 줄로 폈을 때 차지하는 가로 폭(인치). 접히지 않는 짧은 글의 자리를 잡을 때 쓴다."""
    return sum(char_em(ord(ch)) for ch in text) * size_pt / 72.0


def _units(text: str):
    """줄에 놓을 단위를 (폭_em, 종류)로 내보내는 제너레이터.

    종류는 "space"(줄 시작이면 버려지는 공백)와 "word"(줄에 놓이는 덩이) 둘.
    라틴 등 비공백 연속은 한 단어로 묶어 중간에서 안 끊고, 전각은 글자 하나가
    곧 한 단어라 어디서든 줄바꿈 가능.
    """
    run = 0.0
    has_run = False
    for ch in text:
        o = ord(ch)
        em = char_em(o)
        if ch.isspace():
            if has_run:
                yield run, "word"
                run, has_run = 0.0, False
            yield em, "space"
        elif _is_cjk(o):
            if has_run:
                yield run, "word"
                run, has_run = 0.0, False
            yield em, "word"
        else:
            run += em
            has_run = True
    if has_run:
        yield run, "word"


def line_count(text: str, width_in: float, size_pt: float) -> int:
    """`width_in` 인치 폭 상자에 `size_pt` 크기로 담을 때 접히는 줄 수.

    빈 문자열도 한 줄로 셈(글상자는 비어도 한 줄 자리를 차지). 상자보다 넓은 한
    단어는 쪼개지 않고 한 줄에 흘러넘치게 둠(라틴 긴 단어의 현실적 처리).
    """
    if not text:
        return 1
    max_w = max(width_in, 0.01)
    em = size_pt / 72.0  # 이 크기에서 1em 의 인치 폭

    lines = 1
    cur = 0.0  # 현재 줄에 놓인 폭(끝에 매달린 공백 제외)
    pending = 0.0  # 다음 단어 앞 공백. 줄바꿈되면 버려짐

    for width_em, kind in _units(text):
        w = width_em * em
        if kind == "space":
            if cur > 0.0:  # 줄 맨 앞 공백은 무시
                pending += w
            continue
        if cur > 0.0 and cur + pending + w > max_w:
            lines += 1
            cur = w  # 새 줄로 내리며 앞 공백은 버림
        else:
            cur += pending + w
        pending = 0.0
    return lines
