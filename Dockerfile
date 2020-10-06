FROM registry.hub.docker.com/library/python:3.6.8-alpine3.8
ARG proxy=

# set the proxy for pip
ENV http_proxy=$proxy
ENV https_proxy=$proxy
ENV HTTP_PROXY=$proxy
ENV HTTPS_PROXY=$proxy

RUN apk add --no-cache --virtual .build-deps gcc musl-dev g++ linux-headers

# install aviso requirements
WORKDIR /aviso-rest
COPY . .
RUN set -eux && pip install --editable .

RUN set -eux && pip install --editable frontend

RUN apk --no-cache add curl

CMD aviso-rest