"""레이아웃 엔진의 계약(contract) 스펙.

여기 담긴 4가지가 곧 엔진이 지켜야 하는 약속이다. 아직 layout 구현이 없어
전부 실패한다(TDD red). 구현이 이 스펙을 초록으로 만들면 계약이 성립한다.
"""

from ir_pptx.layout import layout


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
