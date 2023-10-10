FROM python:3.9
RUN mkdir -p /var/lib/om

WORKDIR /var/lib/om

COPY . /var/lib/om

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    pip install --upgrade pip && \
    pip3 install -r requirements.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /var/lib/om/pilot/server

CMD ["python", "llmserver.py"]