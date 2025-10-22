FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /project

RUN apt update -y && \
    apt install -y python3-dev \
    gcc \
    musl-dev \
    libpq-dev \
    nmap && \
    rm -rf /var/lib/apt/lists/*

COPY alembic /project/alembic/
COPY alembic.ini /project/
COPY requirements.txt /project/
COPY main.py /project/
COPY config.yml /project/
COPY app /project/app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# RUN alembic upgrade head

CMD ["python", "main.py"]
