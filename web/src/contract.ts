// 두 렌더러가 같은 결과를 내려면 미리 합의해야 하는 값들.
//
// 백엔드 레이아웃 엔진은 글자가 얼마나 넓고 한 줄이 얼마나 높은지를 전제하고 좌표를
// 계산한다. 그 전제가 렌더러와 다르면 좌표가 아무리 정확해도 화면과 파일이 갈라진다.
// 그래서 폰트와 줄 높이는 IR 에 실리는 값이 아니라 양쪽이 미리 맞춰 두는 계약이다.
//
// 같은 값을 보는 곳:
//   FONT_FACE   `web/src/index.css` 의 @font-face, `src/ir_pptx/font_metrics.py` 의 폭 표
//   LINE_RATIO  `src/ir_pptx/layout.py` 의 LINE_RATIO
//
// pptxgenjs 를 import 하지 않는 별도 모듈로 둔 이유: 미리보기가 이 값을 쓰는데,
// pptx.ts 에 두면 무겁게 지연 로드하던 pptxgenjs 가 초기 번들로 딸려 들어온다.

export const FONT_FACE = "Pretendard";

// 한 줄이 차지하는 세로 = 글자 크기 × 이 비율.
export const LINE_RATIO = 1.25;

// 글상자 안쪽 여백(pt). pptxgenjs 가 이 값을 안 넘기면 파워포인트가 기본 여백
// (좌우 각 7pt = 0.097in)을 넣는다. 그러면 글이 놓이는 폭이 IR 의 w 보다 0.194in
// 좁아져 미리보기보다 파일에서 줄이 먼저 접힌다. DOM 쪽은 여백이 없으므로 0 으로 맞춘다.
export const TEXT_INSET = 0;
