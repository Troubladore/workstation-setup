FROM python:3.11-slim
ARG PIP_PYSPARK=3.5.1
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv && \
    uv pip install --system pyspark==${PIP_PYSPARK}
WORKDIR /opt/app
COPY . /opt/app
RUN uv pip install --system .
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENTRYPOINT ["datakit-spark"]
