from multiprocessing.sharedctypes import Value
import gradio as gr 
from datetime import timedelta
from srt import Subtitle
import srt
import os
import openai
import moviepy.editor as mp
from pydub import AudioSegment
import time
from fastapi import FastAPI
import io
import tempfile 

def excute(api_key, mp4_file_path,model):
    print("処理を開始します...")
    openai.api_key = api_key
    if model not in get_available_models(api_key):
        return "エラー：使用できないモデルです。","エラー：使用できないモデルです。"
    
    print("mp4ファイルをmp3に変換しています...")
    format = os.path.splitext(mp4_file_path.name.split("/")[-1])[1].replace(".", "")
    print(format)
    audio_clip = AudioSegment.from_file(mp4_file_path.name, format=format)
    audio_segments_bytes = []
    print("変換が完了しました。ファイルを作成します...")
    interval_ms = 480_000 # 60秒 = 60_000ミリ秒

    print("音声ファイルを分割しています...")
    n_splits = len(audio_clip) // interval_ms
    for i in range(n_splits + 1):
        #開始、終了時間
        start = i * interval_ms
        end = (i + 1) * interval_ms
        #分割
        split_audio = audio_clip[start:end]
        
        buffer = io.BytesIO()
        split_audio.export(buffer, format="mp3")
        audio_segments_bytes.append(buffer.getvalue())
    
    print("文字起こしをしています...")
    transcription_list = []
    for audio_bytes in audio_segments_bytes:
        transcription = ""

        # 一時ファイルを使用して物理ファイルを作成します。
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_audio_file:
            temp_audio_file.write(audio_bytes)
            temp_audio_file.flush()  # ディスクに書き込む
            # 一時ファイルを開き直す
            with open(temp_audio_file.name, 'rb') as file_obj:
                # ファイルオブジェクトをtranscribeメソッドに渡す
                transcription = openai.Audio.transcribe("whisper-1", file_obj, language='ja')

    transcription_list.append(transcription.text)

    pre_summary = ""
    
    print("議事録を作成中です...")
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

        time.sleep(60)
    prompt = """
    あなたは、プロの議事録作成者です。
    以下の制約条件、内容を元に要点をまとめ、議事録を作成してください。

    # 制約条件
    ・要点をまとめ、簡潔に書いて下さい。
    ・誤字・脱字があるため、話の内容を予測して置き換えてください。
    ・見やすいフォーマットにしてください。

    # 内容
    """ + pre_summary
    
    print("要約を作成中です...")
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.0,
    )
    print("処理が完了しました。")
    # result = "\n\n\n".join([transcription_list, response['choices'][0]['message']['content']])
    return  response['choices'][0]['message']['content']
    
def get_available_models(api_key):
    openai.api_key = api_key
    tempmodels = []
    response = openai.Model.list()
    for model in response['data']:
        if 'gpt' in model['id']:
            tempmodels.append(model['id'])
            
    return tempmodels
    
models = [
    'gpt-3.5-turbo-16k-0613',
    'gpt-3.5-turbo-16k',
    'gpt-4',
    'gpt-4-0314',
    'gpt-3.5-turbo-0613',
    'gpt-3.5-turbo-instruct-0914',
    'gpt-3.5-turbo-0301',
    'gpt-3.5-turbo-instruct',
    'gpt-3.5-turbo',
    'gpt-4-0613'
]

meeting = gr.outputs.Textbox(label="議事録データ")
with gr.Blocks() as inter:
    with gr.Row():
        with gr.Column():
            api_key = gr.inputs.Textbox(label="APIキー")
            api_list = gr.inputs.Dropdown(label="モデル", choices=models)
            file = gr.inputs.File(label="動画ファイル")
            excute_Button = gr.Button(label="実行", type="button")
            excute_Button.click(excute, [api_key, file, api_list], meeting)      
        with gr.Column():
            meeting.render()
        
app = FastAPI()
app = gr.mount_gradio_app(app, inter,path="/")