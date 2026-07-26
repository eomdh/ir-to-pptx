"""텍스트 줄 수 추정.

폰트 파일 없이 글자 폭을 em 비율로 어림해, 한 글상자에서 텍스트가 몇 줄로
접히는지 세는 모듈. 레이아웃(`layout.py`)이 이 값으로 불릿과 문단의 세로 높이를 잡음.

진짜 폰트 메트릭 대신 어림을 쓰는 이유: 폰트 엔진은 이 데모의 목적 대비 과함.
대신 두 가지를 지키는 게 목표.

  1. 결정성 — 같은 입력은 항상 같은 줄 수. 미리보기와 pptx 파일이 같은 IR 을
     받는다는 전제의 뿌리.
  2. 과소 계산 금지 — 줄 수를 실제보다 적게 잡으면 글상자가 촘촘해져 다음 블록과
     겹침. 그래서 폭을 살짝 넉넉히 잡아 오차를 위쪽으로만 둠.
"""

from __future__ import annotations

# 글자 한 개의 가로 폭을 em(글자 높이 = 1em) 비율로 어림한 값.
_CJK_EM = 1.0  # 한글, 한자, 가나 같은 전각은 대략 정사각
_SPACE_EM = 0.28  # 공백은 좁게
_OTHER_EM = 0.5  # 라틴, 숫자, 문장부호 평균


def _is_cjk(o: int) -> bool:
    # 한 글자씩 줄바꿈이 되는 전각 문자 범위.
    return (
        0xAC00 <= o <= 0xD7A3  # 한글 음절
        or 0x1100 <= o <= 0x11FF  # 한글 자모
        or 0x3130 <= o <= 0x318F  # 한글 호환 자모
        or 0x3040 <= o <= 0x30FF  # 히라가나, 가타카나
        or 0x4E00 <= o <= 0x9FFF  # CJK 한자
        or 0xFF00 <= o <= 0xFF60  # 전각 기호
    )


def _char_em(ch: str) -> float:
    o = ord(ch)
    if _is_cjk(o):
        return _CJK_EM
    if ch.isspace():
        return _SPACE_EM
    return _OTHER_EM


def _units(text: str):
    """줄에 놓을 단위를 (폭_em, 종류)로 내보내는 제너레이터.

    종류는 "space"(줄 시작이면 버려지는 공백)와 "word"(줄에 놓이는 덩이) 둘.
    라틴 등 비공백 연속은 한 단어로 묶어 중간에서 안 끊고, CJK 는 글자 하나가
    곧 한 단어라 어디서든 줄바꿈 가능.
    """
    run = 0.0
    has_run = False
    for ch in text:
        o = ord(ch)
        if ch.isspace():
            if has_run:
                yield run, "word"
                run, has_run = 0.0, False
            yield _SPACE_EM, "space"
        elif _is_cjk(o):
            if has_run:
                yield run, "word"
                run, has_run = 0.0, False
            yield _CJK_EM, "word"
        else:
            run += _OTHER_EM
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
