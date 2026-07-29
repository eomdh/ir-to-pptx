"""줄 수 계산 스펙.

폭은 Pretendard 실측 표에서 오지만 줄바꿈 규칙까지 폰트가 정해 주지는 않는다.
레이아웃이 기대는 성질(빈 값도 한 줄, 좁을수록 더 많은 줄, 안 쪼개지는 단어,
결정성)과 표를 쓴다는 사실 자체를 못박는다.
"""

from ir_pptx.metrics import char_em, line_count

# 본문 기본값. layout 의 CONTENT_W, PARA_SIZE 와 같은 값이다.
WIDTH = 8.8
SIZE = 16


def test_빈_문자열도_한_줄로_센다():
    assert line_count("", WIDTH, SIZE) == 1


def test_상자에_들어가는_짧은_텍스트는_한_줄():
    assert line_count("짧은 한 줄", WIDTH, SIZE) == 1


def test_긴_한글은_폭에_맞춰_여러_줄로_접힌다():
    # 한글 폭은 0.8643em 이라 16pt, 8.8인치에 45자가 든다. 100자면 세 줄이다.
    assert line_count("가" * 100, WIDTH, SIZE) == 3


def test_좁은_상자는_같은_텍스트를_더_많은_줄로_접는다():
    text = "가" * 60
    assert line_count(text, 4.0, SIZE) > line_count(text, WIDTH, SIZE)


def test_안_쪼개지는_긴_단어는_넘쳐도_한_줄로_둔다():
    # 공백 없는 라틴 한 덩이는 중간에서 못 끊는다. 상자보다 넓어도 한 줄로 흘려보낸다.
    assert line_count("x" * 100, 1.0, SIZE) == 1


def test_공백은_줄바꿈_지점이_된다():
    # 같은 글자 수라도 공백으로 나뉘면 단어 경계에서 접혀 여러 줄이 된다.
    assert line_count("word " * 50, WIDTH, SIZE) > 1


def test_같은_입력은_같은_줄_수를_낸다():
    text = "가나다 " * 30
    assert line_count(text, WIDTH, SIZE) == line_count(text, WIDTH, SIZE)


def test_글자마다_실제_폭을_쓴다():
    # 어림값이면 라틴이 전부 같은 폭이라 두 줄이 같은 길이로 접힌다. 표를 쓰면
    # 좁은 글자(i 0.218em)와 넓은 글자(W 0.915em)가 네 배 넘게 갈린다.
    assert char_em(ord("i")) < char_em(ord("W")) / 4
    # 공백을 넣어 끊길 수 있게 해야 폭 차이가 줄 수로 드러난다.
    assert line_count("i " * 40, 2.0, SIZE) < line_count("W " * 40, 2.0, SIZE)


def test_한글은_전각보다_좁다():
    # 정사각으로 치면 한 줄에 들어갈 글자를 실제보다 적게 잡아 빈 자리가 남는다.
    assert char_em(ord("가")) == 0.8643


def test_표에_없는_글자는_전각으로_넉넉히_친다():
    # Pretendard 에 한자가 없다. 브라우저가 다른 폰트로 그리므로 폭을 알 수 없고,
    # 줄 수를 적게 잡지 않는 쪽으로 기운다.
    assert char_em(ord("漢")) == 1.0
