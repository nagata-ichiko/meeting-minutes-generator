FROM python:3.7-slim

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# システムパッケージの更新と必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    git \
    python3-tk \
    portaudio19-dev \
    ffmpeg \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*  

RUN pip install --upgrade pip

# ソースファイルのコピー
COPY requirements.txt /root/
COPY main.py /root/
WORKDIR /root/
RUN pip install -r requirements.txt

# RUN mkdir -p /usr/local/lib/python3.9/site-packages/gradio/
# # 不足しているファイルをダウンロードし、適切な場所に配置
# RUN wget -O /usr/local/lib/python3.9/site-packages/gradio/frpc_linux_aarch64_v0.2 https://cdn-media.huggingface.co/frpc-gradio-0.2/frpc_linux_aarch64 && \
#     chmod +x /usr/local/lib/python3.9/site-packages/gradio/frpc_linux_aarch64_v0.2

# アプリケーションのコマンドを実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
