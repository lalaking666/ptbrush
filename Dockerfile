FROM python:3.10-slim
RUN sed -i s@/deb.debian.org/@/mirrors.tuna.tsinghua.edu.cn/@g /etc/apt/sources.list.d/debian.sources
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV WEB_PORT 8000
COPY ptbrush /app

ADD docker-entrypoint.sh docker-entrypoint.sh

COPY requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y gosu && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && chmod +x docker-entrypoint.sh \
    && useradd app

WORKDIR /app

VOLUME ["/app/data"]

# Expose web interface port
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["start"]