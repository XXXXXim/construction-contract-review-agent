FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

COPY data ./data
COPY app ./app

# API 키는 실행 시 -e 또는 --env-file 로 넘긴다. 이미지에 넣지 않는다.
ENV LLM_PROVIDER=fake EMBEDDING_PROVIDER=none
EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
