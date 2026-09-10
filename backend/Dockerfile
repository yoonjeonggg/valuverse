FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 컨테이너에서는 마이그레이션으로 스키마를 관리한다.
ENV AUTO_CREATE_TABLES=false

EXPOSE 8000

# 시작 시 최신 스키마로 이관 후 서버 기동
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
