# ir-to-pptx

마크다운을 **좌표까지 다 계산된 평면 IR(JSON)** 로 바꿔 내려주는 FastAPI 백엔드와,
그 IR 하나로 **브라우저에서 PPTX 파일을 직접 만드는** React 프론트.

> 서버는 파일을 만들지 않는다. 좌표는 서버가 한 번 계산하고, 그림은 브라우저가 그린다.

```
마크다운  ──►  FastAPI 레이아웃 엔진  ──►  평면 IR(JSON)  ─┬─►  DOM 미리보기
                                                    └─►  pptxgenjs → .pptx 다운로드
```

같은 IR 이 미리보기와 파일 두 렌더러를 똑같이 구동한다. 그래서 화면에 보이는 대로 파일이 나온다.

## 실행

```bash
docker compose up
# http://localhost:8000
```

## 개발

```bash
# 백엔드
uv sync
uv run uvicorn ir_pptx.main:app --reload

# 프론트
cd web && pnpm install && pnpm dev
```

## License

MIT
