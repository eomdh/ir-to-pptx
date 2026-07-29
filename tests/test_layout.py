"""레이아웃 엔진의 계약(contract) 스펙.

여기 담긴 것이 곧 엔진이 지켜야 하는 약속이다. 좌표를 픽셀까지 맞추기보다,
블록이 겹치지 않고 세로 리듬이 고르며 같은 입력이 같은 좌표를 낸다는 성질을 못박는다.
"""

import pytest

from ir_pptx.blocks import Bullet, Heading, Kpi, KpiTile, Table
from ir_pptx.layout import (
    BULLET_GAP,
    BULLET_SIZE,
    CONTENT_W,
    LINE_RATIO,
    PARA_SIZE,
    _block_height,
    _bullet_box_h,
    _kpi_h,
    _table_row_heights,
    layout,
)
from ir_pptx.metrics import line_count


def _texts(slide):
    return [e for e in slide.elements if e.type == "text"]


def test_제목과_불릿이_한_슬라이드에_위에서_아래로_배치된다():
    deck = layout("# 분기 실적\n\n- 매출 증가\n- 이익 개선\n")

    assert len(deck.slides) == 1
    texts = _texts(deck.slides[0])
    # 제목은 굵게, 불릿이 아니다.
    assert any(t.text == "분기 실적" and t.bold and not t.bullet for t in texts)
    bullets = [t for t in texts if t.bullet]
    assert [b.text for b in bullets] == ["매출 증가", "이익 개선"]
    # 결정적 세로 흐름: 불릿은 위에서 아래로 쌓인다.
    assert bullets[0].y < bullets[1].y


def test_h1마다_새_슬라이드가_열린다():
    # 슬라이드 분할 규칙 = H1('#'). 제목이 곧 슬라이드의 시작이다.
    deck = layout("# 첫 장\n\n- a\n\n# 둘째 장\n\n- b\n")
    assert len(deck.slides) == 2


def test_긴_불릿_목록은_넘치면_다음_슬라이드로_이어진다():
    md = "# 큰 목록\n\n" + "\n".join(f"- 항목 {i}" for i in range(40))
    deck = layout(md)

    # 한 슬라이드에 다 안 들어가므로 이어지는 슬라이드가 생긴다.
    assert len(deck.slides) >= 2
    # 어떤 요소도 슬라이드 세로 경계를 넘지 않는다(넘칠 것은 다음 장으로 갔다).
    for slide in deck.slides:
        for t in _texts(slide):
            assert t.y + t.h <= deck.height + 1e-9
    # 불릿은 하나도 잃지 않는다(총 개수 보존).
    total = sum(len([t for t in _texts(s) if t.bullet]) for s in deck.slides)
    assert total == 40


def test_2단_컬럼은_왼쪽_오른쪽에_나란히_배치된다():
    md = "# 두 단\n\n::: columns\n- 왼쪽 A\n- 왼쪽 B\n||\n- 오른쪽 A\n:::\n"
    els = layout(md).slides[0].elements

    bullets = [e for e in els if e.type == "text" and e.bullet]
    left = [b for b in bullets if b.text.startswith("왼쪽")]
    right = [b for b in bullets if b.text.startswith("오른쪽")]
    assert len(left) == 2 and len(right) == 1
    # 오른쪽 칸은 왼쪽 칸보다 오른쪽에 있다.
    assert min(r.x for r in right) > max(b.x for b in left)
    # 두 칸의 첫 줄은 같은 높이에서 시작한다.
    assert left[0].y == right[0].y


def test_표는_헤더와_각_셀을_그린다():
    md = "# 표\n\n| 지역 | 매출 |\n|---|---|\n| 서울 | 42 |\n| 부산 | 18 |\n"
    els = layout(md).slides[0].elements

    texts = [e.text for e in els if e.type == "text"]
    for want in ["지역", "매출", "서울", "42", "부산", "18"]:
        assert want in texts
    # 헤더 셀은 볼드로 그린다.
    assert any(e.type == "text" and e.text == "지역" and e.bold for e in els)
    # 헤더 배경 사각형이 있다.
    assert any(e.type == "shape" and e.fill == "EEF2F7" for e in els)


def test_같은_마크다운은_같은_좌표를_낸다():
    # 결정성 = "보이는 대로 나온다"의 뿌리. DOM 미리보기와 pptx 가 같은 IR 을
    # 받으려면 같은 입력이 항상 같은 좌표여야 한다.
    md = "# 결정성\n\n- 가\n- 나\n- 다\n"
    assert layout(md).model_dump() == layout(md).model_dump()


def test_본문_소제목_h2가_사라지지_않고_텍스트로_들어간다():
    # 예전엔 H2 블록이 레이아웃에서 조용히 사라졌다. 이제는 소제목으로 그린다.
    deck = layout("# 슬라이드\n\n## 소제목\n\n- 항목\n")
    texts = _texts(deck.slides[0])
    sub = [t for t in texts if t.text == "소제목"]
    assert len(sub) == 1
    assert sub[0].bold and not sub[0].bullet
    # 소제목은 제목(H1)보다 아래, 불릿보다 위에 온다.
    title_y = next(t.y for t in texts if t.text == "슬라이드")
    bullet_y = next(t.y for t in texts if t.bullet)
    assert title_y < sub[0].y < bullet_y


def test_kpi_펜스는_타일마다_카드와_값_라벨을_만든다():
    md = (
        "# 지표\n\n"
        "```kpi\n"
        '[{"label":"매출","value":"63억","delta":"+18%"},{"label":"이탈률","value":"5.1%"}]\n'
        "```\n"
    )
    els = layout(md).slides[0].elements

    cards = [e for e in els if e.type == "shape" and e.shape == "roundRect"]
    assert len(cards) == 2
    texts = [e.text for e in els if e.type == "text"]
    assert "63억" in texts and "매출" in texts and "+18%" in texts
    # 두 타일은 같은 높이에서 가로로 나란히 놓인다.
    assert cards[0].y == cards[1].y
    assert cards[0].x < cards[1].x


def test_긴_문단은_접히는_줄_수만큼_세로를_차지한다():
    # 예전엔 문단이 늘 한 줄 높이였다. 이제는 폭에 맞춰 접히는 줄 수만큼 상자가 큰다.
    long = "가" * 120
    para = next(t for t in _texts(layout(f"# 긴 문단\n\n{long}\n").slides[0]) if t.text == long)

    n = line_count(long, CONTENT_W, PARA_SIZE)
    assert n >= 3
    # 상자는 글이 차지하는 만큼만. 블록 뒤 여백은 상자 밖에 있다.
    assert para.h == round(n * PARA_SIZE * LINE_RATIO / 72, 3)


def test_긴_불릿은_다음_블록을_그만큼_아래로_민다():
    # 줄바꿈을 세지 않던 시절엔 긴 불릿 아래 블록이 그 위로 겹쳐 올라왔다.
    def second_bullet_y(md):
        bullets = [t for t in _texts(layout(md).slides[0]) if t.bullet]
        return bullets[1].y

    short = second_bullet_y("# 목록\n\n- 짧은 항목\n- 다음 항목\n")
    long = second_bullet_y("# 목록\n\n- " + "가" * 120 + "\n- 다음 항목\n")
    assert long > short


def test_인라인_강조는_조각_runs로_나뉜다():
    # **굵게** 와 *기울임* 이 조각별 스타일로 갈린다. text 는 조각을 이어붙인 평문.
    slide = layout("# 강조\n\n- 보통 **굵게** 또 *기울임* 끝\n").slides[0]
    bullet = next(t for t in _texts(slide) if t.bullet)

    assert bullet.text == "보통 굵게 또 기울임 끝"
    assert bullet.runs is not None
    styled = {(r.text, r.bold, r.italic) for r in bullet.runs}
    assert ("굵게", True, False) in styled
    assert ("기울임", False, True) in styled
    # 조각을 이어붙이면 평문과 같다(줄 수 계산의 근거).
    assert "".join(r.text for r in bullet.runs) == bullet.text


def test_강조가_없으면_runs는_비어_평문으로_남는다():
    # 강조가 없는 흔한 경우엔 runs 를 None 으로 둬 IR 을 작게 유지한다.
    bullet = next(t for t in _texts(layout("# 평범\n\n- 그냥 한 줄\n").slides[0]) if t.bullet)
    assert bullet.runs is None
    assert bullet.text == "그냥 한 줄"


def test_차트_펜스는_위치잡힌_차트요소가_된다():
    md = (
        "# 차트\n\n"
        "```chart\n"
        '{"kind":"bar","categories":["A","B"],"series":[{"name":"매출","data":[1,2]}]}\n'
        "```\n"
    )
    deck = layout(md)

    charts = [e for e in deck.slides[0].elements if e.type == "chart"]
    assert len(charts) == 1
    chart = charts[0]
    assert chart.spec.kind == "bar"
    assert chart.spec.categories == ["A", "B"]
    # 차트가 놓일 자리가 실제 크기를 갖고 슬라이드 안에 있다.
    assert chart.w > 0 and chart.h > 0
    assert chart.x >= 0 and chart.y >= 0
    assert chart.x + chart.w <= deck.width + 1e-9


def test_블록_뒤_여백은_줄_수와_무관하게_일정하다():
    """예전에는 줄 높이 상수 하나가 줄 간격과 블록 여백을 겸해서, 줄이 늘면 여백도
    배로 늘었다. 상자는 글 높이만 잡고 여백은 상자 밖에 두므로 이제 일정해야 한다."""
    short = Bullet(text="짧다", level=0, runs=[])
    long = Bullet(text="가" * 120, level=0, runs=[])
    w = CONTENT_W

    # 두 불릿의 줄 수는 다르지만
    assert _bullet_box_h(long, w) > _bullet_box_h(short, w)
    # 상자 뒤에 붙는 여백은 같다
    for b in (short, long):
        assert _block_height(b, w) - _bullet_box_h(b, w) == pytest.approx(BULLET_GAP)


def test_글상자_높이는_글이_차지하는_만큼만_잡는다():
    """상자에 여백까지 넣으면 위쪽 정렬이라 남는 자리가 아래에 깔리고, 줄 수가 늘수록
    그 자리가 커져 세로 리듬이 깨진다."""
    b = Bullet(text="가" * 120, level=0, runs=[])
    lines = _bullet_box_h(b, CONTENT_W) / (BULLET_SIZE * LINE_RATIO / 72)
    assert lines == pytest.approx(round(lines))


def test_표는_긴_칸이_있는_행만_높아진다():
    """행 높이가 고정이던 시절엔 긴 칸 글이 아래 행 위로 넘쳤다. 이제 그 행만 큰다."""
    long_cell = "대형 고객 갱신 협상을 3분기 내 마무리하고 이탈 위험군을 별도로 관리한다"
    t = Table(header=["채널", "설명"], rows=[["파트너", "짧다"], ["다이렉트", long_cell]])
    header_h, short_h, long_h = _table_row_heights(t, CONTENT_W)

    assert header_h == short_h  # 한 줄짜리끼리는 같고
    assert long_h > short_h  # 접힌 행만 커진다


def test_kpi_타일은_라벨이_접히면_함께_높아진다():
    """타일은 한 행이라 높이를 공유한다. 가장 많이 접힌 라벨이 행 높이를 정한다."""
    short = Kpi(tiles=[KpiTile(label=f"라벨{i}", value="1", delta=None) for i in range(4)])
    long = Kpi(
        tiles=[
            KpiTile(label="엔터프라이즈 신규 고객 수", value="1", delta=None),
            *(KpiTile(label=f"라벨{i}", value="1", delta=None) for i in range(3)),
        ]
    )
    assert _kpi_h(long, CONTENT_W) > _kpi_h(short, CONTENT_W)


def test_긴_소제목은_접히는_줄_수만큼_자리를_차지한다():
    long = (
        "파트너 채널 확대와 마켓플레이스 재편을 통한 하반기 매출 구조 개선 방향"
        " 그리고 분기별 실행 계획과 점검 지표"
    )
    assert _block_height(Heading(text=long, level=2), CONTENT_W) > _block_height(
        Heading(text="짧은 소제목", level=2), CONTENT_W
    )


def test_kpi_라벨과_delta는_가로로_겹치지_않는다():
    """둘은 같은 줄의 왼쪽과 오른쪽이다. 폭을 나눠 갖지 않으면 라벨이 길 때
    delta 위로 글이 올라와 겹친다."""
    # 타일이 넷이면 한 칸이 좁아져 긴 라벨이 실제로 접힌다.
    md = (
        "# 지표\n\n```kpi\n"
        '[{"label":"엔터프라이즈 신규 고객 수","value":"240곳","delta":"+31%"},'
        '{"label":"매출","value":"63억","delta":"+18%"},'
        '{"label":"이탈률","value":"5.1%","delta":"-0.6%p"},'
        '{"label":"NPS","value":"48","delta":"+6"}]\n```\n'
    )
    texts = _texts(layout(md).slides[0])
    label = next(t for t in texts if t.text == "엔터프라이즈 신규 고객 수")
    delta = next(t for t in texts if t.text == "+31%")

    assert label.h > delta.h  # 라벨은 접혀서 더 높고
    assert label.x + label.w <= delta.x  # 가로로는 서로 침범하지 않는다
