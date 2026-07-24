# 프론트를 먼저 빌드하고 산출물만 런타임 이미지로 넘긴다.
# node 툴체인이 최종 이미지에 남지 않는다.
FROM node:22-alpine AS web

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable

WORKDIR /web

# 의존성 먼저 굳혀 레이어 캐시를 살린다. pnpm-workspace.yaml 은 esbuild 의
# 설치 스크립트 허용 목록이라 이 단계에 같이 있어야 한다.
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY web/ ./
RUN pnpm build


FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# 의존성 해석을 먼저 굳혀 레이어 캐시를 살린다. README 는 hatchling 이
# 패키지 메타데이터로 읽으므로 같이 넣는다.
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev

# 빌드된 프론트. main.py 가 여기를 정적으로 서빙하고, 같은 오리진이라
# CORS 설정이 필요 없다.
COPY --from=web /web/dist ./web-dist

EXPOSE 8000

# 동기화된 venv 를 직접 부른다. uv run 은 실행할 때마다 의존성을 다시 맞춰
# 기동이 느려진다.
CMD [".venv/bin/uvicorn", "ir_pptx.main:app", "--host", "0.0.0.0", "--port", "8000"]
