FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ unixodbc unixodbc-dev freetds-dev freetds-bin \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /opt/app
COPY . /opt/app
RUN uv pip install --system .

ENTRYPOINT ["datakit-sqlsrv"]
