FROM openeuler/openeuler:22.03-lts-sp1

RUN yum update -y \
    && yum install -y shadow

RUN groupadd -g 1001 dbgpt \
    && useradd -u 1001 -g dbgpt -s /bin/bash -m dbgpt


RUN cd /home/dbgpt

RUN yum install -y make gcc gcc-c++ postgresql-devel zlib-devel openssl-devel bzip2-devel ncurses-devel gdbm-devel readline-devel sqlite-devel libffi-devel tk-devel xz-devel \
    && yum install -y openssl-devel openssl \
    && yum install -y wget

RUN wget https://repo.huaweicloud.com/python/3.9.0/Python-3.9.0.tgz \
    && tar -xzf Python-3.9.0.tgz \
    && cd Python-3.9.0 \
    && ./configure --prefix=/home/dbgpt/python --with-ssl \
    && make \
    && make install 

ENV PATH="/home/dbgpt/python/bin:${PATH}"

RUN python3 -V 

WORKDIR /home/dbgpt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV APPLICATION_PATH=/home/dbgpt/pilot/config.ini

RUN pip3 install --upgrade pip \
    && pip3 install -r requirements.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple

USER dbgpt

CMD ["python3", "pilot/server/llmserver.py"]