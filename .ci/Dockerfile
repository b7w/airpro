FROM python:3.12-slim-bookworm

ENV VERSION="0.1.0"
ENV WHEEL="airpro-$VERSION-py3-none-any.whl"


RUN apt-get update -qq && \
    apt-get install -yqq curl openssh-client && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get -qq clean


COPY dist/$WHEEL dist/requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt && pip install --no-cache-dir /app/$WHEEL

ENTRYPOINT ["airpro"]
