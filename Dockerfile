FROM python:3.9

RUN groupadd -g 1001 dbgpt \
    && useradd -u 1001 -g dbgpt -s /bin/bash -m dbgpt

WORKDIR /home/dbgpt

COPY . .

RUN chown -R dbgpt:dbgpt /home/dbgpt
RUN chmod -R 777 /home/dbgpt

ENV PYTHONUNBUFFERED=1
ENV APPLICATION_PATH=/home/dbgpt/pilot/config.ini

RUN apt-get update && \
    pip install --upgrade pip && \
    pip3 install -r requirements.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple

USER dbgpt

CMD ["python", "pilot/server/llmserver.py"]