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
    audio = AudioSegment.from_file(mp4_file_path.name, format=format)
    print("変換が完了しました。ファイルを作成します...")

    output_folder = "./output/"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print("音声ファイルを分割しています...")
    interval_ms = 480_000 # 60秒 = 60_000ミリ秒    
    mp3_file_path_list = []
    n_splits = len(audio) // interval_ms
    for i in range(n_splits + 1):
        #開始、終了時間
        start = i * interval_ms
        end = (i + 1) * interval_ms
        #分割
        split = audio[start:end]
        #出力ファイル名
        output_file_name = output_folder +  os.path.splitext(mp4_file_path.name.split("/")[-1])[0] + "_" + str(i) + ".mp3"
        #出力
        split.export(output_file_name, format="mp3")

        #音声ファイルリストに追加
        mp3_file_path_list.append(output_file_name)
        
    del audio
    print("文字起こしをしています...")
    transcription_list = []
    for mp3_file_path in mp3_file_path_list:
        with open(mp3_file_path, 'rb') as audio_file:
            transcription = openai.Audio.transcribe("whisper-1", audio_file, language='ja')
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

    result ="[文字起こし結果]"    
    for i in transcription_list:
        result += i + "\n"
        
    result += response['choices'][0]['message']['content']
    
    print("ファイルを削除します")
    try:
        os.remove(mp4_file_path.name)
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                os.remove(os.path.join(root, file))
        
    except Exception as e:
        print(f"Error deleting original video file {mp4_file_path}: {e}")
    
    return result
    # return  response['choices'][0]['message']['content']
    
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
    caption = gr.Markdown(
        """
        ### 動画や音声を元に会議録を自動生成するためのアプリです。
        ### 注意事項：このアプリは、OpenAIのAPIキーが必要です。APIキーを入力してください。
        ### サーバーのメモリが512MなのでそれM以下のファイルを使用してください(200Mまでは動作確認済み)。大きいファイルだと正常に動作しない場合があります。音声ファイルがおすすめです。
        ### 無料サーバーなのでちょっと重いです。反応をちょっとだけ待ってください。
        """
    )
    with gr.Row():
        with gr.Column():
            api_key = gr.inputs.Textbox(label="APIキー")
            api_list = gr.inputs.Dropdown(label="モデル", choices=models)
            file = gr.inputs.File(label="動画ファイル")
            excute_Button = gr.Button(value="実行", type="button")
            excute_Button.click(excute, [api_key, file, api_list], meeting)      
        with gr.Column():
            meeting.render()

app = FastAPI()
app = gr.mount_gradio_app(app, inter,path="/")