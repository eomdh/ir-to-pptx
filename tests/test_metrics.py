"""줄 수 추정 스펙.

폰트 파일 없이 어림하는 값이라 픽셀까지 맞지는 않는다. 대신 레이아웃이 기대는
성질(빈 값도 한 줄, 좁을수록 더 많은 줄, 안 쪼개지는 단어, 결정성)을 못박는다.
"""

from ir_pptx.metrics import line_count

# 본문 기본값. layout 의 CONTENT_W, PARA_SIZE 와 같은 값이다.
WIDTH = 8.8
SIZE = 16


def test_빈_문자열도_한_줄로_센다():
    assert line_count("", WIDTH, SIZE) == 1


def test_상자에_들어가는_짧은_텍스트는_한_줄():
    assert line_count("짧은 한 줄", WIDTH, SIZE) == 1


def test_긴_한글은_폭에_맞춰_여러_줄로_접힌다():
    # 16pt 에서 한글은 대략 정사각이라 8.8인치에 약 39자가 든다. 100자면 세 줄이다.
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
