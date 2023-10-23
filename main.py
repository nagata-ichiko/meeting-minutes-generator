from multiprocessing.sharedctypes import Value
from io import BytesIO
import gradio as gr 
from datetime import timedelta
from srt import Subtitle
import srt
import os
import openai
import moviepy.editor as mp
from pydub import AudioSegment
import time

# MP4をMP3に変換する（ディスクではなくメモリ上で）
def convert_mp4_to_mp3(mp4_file_content):
    mp4_io = BytesIO(mp4_file_content)
    audio = mp.AudioFileClip(mp4_io)
    mp3_io = BytesIO()
    audio.write_audiofile(mp3_io, codec='mp3')
    mp3_io.seek(0)  # Read/write pointerを先頭に戻す
    return mp3_io

# 音声を文字起こしする
def transcribe_audio(mp3_file_content):
    transcription = openai.Audio.transcribe("whisper-1", BytesIO(mp3_file_content), language='ja')
    return transcription.text

# 音声ファイルを分割する
def split_audio(mp3_file_content, interval_ms):
    audio = AudioSegment.from_file(BytesIO(mp3_file_content))
    audio_segments = []

    n_splits = len(audio) // interval_ms
    for i in range(n_splits + 1):
        start = i * interval_ms
        end = (i + 1) * interval_ms
        split = audio[start:end]
        segment_io = BytesIO()
        split.export(segment_io, format="mp3")
        segment_io.seek(0)  # Read/write pointerを先頭に戻す
        audio_segments.append(segment_io)

    return audio_segments

def execute(api_key, mp4_file, model):  # 引数名を変更
    openai.api_key = api_key
    # 利用可能なモデルをチェックする部分は同じなので、そのまま使用します。

    # メモリ上のファイルコンテンツを直接使用
    mp3_content = convert_mp4_to_mp3(mp4_file.read())

    # 分割間隔を設定
    interval_ms = 480_000  # 例: 8分
    audio_segments = split_audio(mp3_content.getvalue(), interval_ms)

    transcription_list = []
    for audio_segment in audio_segments:
        transcription = transcribe_audio(audio_segment.getvalue())
        transcription_list.append(transcription)
        # ファイル保存は行わず、文字起こし結果をリストに保存

    # ... [以下の要約と議事録作成部分は以前のコードを維持] ...

    pre_summary = ""
    for transcription_part in transcription_list:
        prompt = """
        あなたは、プロの要約作成者です。
        以下の制約条件、内容を元に要点をまとめてください。

        # 制約条件
        ・要点をまとめ、簡潔に書いて下さい。
        ・誤字・脱字があるため、話の内容を予測して置き換えてください。

        # 内容
        """ + transcription_part

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.0,
        )   
        pre_summary += response['choices'][0]['message']['content']
        time.sleep(60)  # APIのレート制限などに対応するためのウェイト

    # ... [議事録作成部分のコード] ...

    # 直接データを返す
    prompt = """
    あなたは、プロの議事録作成者です。
    以下の制約条件、内容を元に要点をまとめ、議事録を作成してください。

    # 制約条件
    ・要点をまとめ、簡潔に書いて下さい。
    ・誤字・脱字があるため、話の内容を予測して置き換えてください。
    ・見やすいフォーマットにしてください。

    # 内容
    """ + pre_summary


    print("議事録を作成中です...")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.0,
    )
    return transcription_list, response['choices'][0]['message']['content']

# 利用可能なモデルのリストやgr.Interfaceの設定など、その他の部分は変更せずにそのまま使用できます。
# ただし、ファイルパスを扱う部分がある場合、それらを適切にBytesIOオブジェクトに置き換える必要があります。
def get_available_models(api_key):
    openai.api_key = api_key
    tempmodels = []
    response = openai.Model.list()
    for model in response['data']:
        if 'gpt' in model['id']:
            tempmodels.append(model['id'])
            
    return tempmodels

models = [
    # ... [モデルのリストがここに続く] ...
]

gr.Interface(
    title="テキストとファイルの入力",
    description="テキストとファイルを入力して処理を実行します。",
    inputs=[
        gr.inputs.Textbox(label="APIキー"),
        gr.inputs.File(label="動画ファイル"),
        gr.inputs.Dropdown(label="モデル",choices=models),
    ],
    outputs=[
        gr.outputs.Textbox(label="文字起こしデータ"),
        gr.outputs.Textbox(label="議事録データ"),
    ],
    fn=execute,
    ).launch(server_name = "0.0.0.0", server_port=7860)