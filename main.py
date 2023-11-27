from multiprocessing.sharedctypes import Value
import gradio as gr 
from datetime import timedelta
import os
import openai
import moviepy.editor as mp
from pydub import AudioSegment
import time
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()
pre_summary = ""
output_folder = "./output/"
def transcription_excute(api_key, mp4_file_path,model):
    openai.api_key = api_key
    transcription_list = []
    print("処理を開始します...")    
    print("mp4ファイルをmp3に変換しています...")
    format = os.path.splitext(mp4_file_path.name.split("/")[-1])[1].replace(".", "")
    print(format)
    audio = AudioSegment.from_file(mp4_file_path.name, format=format)
    print("変換が完了しました。ファイルを作成します...")


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

    for mp3_file_path in mp3_file_path_list:
        with open(mp3_file_path, 'rb') as audio_file:
            transcription = openai.Audio.transcribe("whisper-1", audio_file, language='ja')
        transcription_list.append(transcription.text)

    result =""   

    for i in transcription_list:
        result += i + "\n"    
    print("ファイルを削除します")
    try:
        os.remove(mp4_file_path.name)
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                os.remove(os.path.join(root, file))
        
    except Exception as e:
        print(f"Error deleting original video file {mp4_file_path}: {e}")
        
    return result

def pre_summary_excute(api_key,model,transcription,pre_summary_text):
    print(transcription)
    transcription_list = transcription.split("\n")
    print(transcription_list)
    openai.api_key = api_key
    pre_summary = ""
    for transcription_part in transcription_list:
        print("議事録を作成中です...")
        prompt = pre_summary_text +"""
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
        
    return pre_summary

def summary_excute(api_key,model,pre_summary_out,summary_text):
    openai.api_key = api_key
    prompt = summary_text + """
    # 内容
    """ + pre_summary_out
    print(pre_summary_out)
    print("要約を作成中です...")
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.0,
    )
    print("処理が完了しました。")   
    return  response['choices'][0]['message']['content']
    
def get_available_models(api_key):
    openai.api_key = api_key
    tempmodels = []
    response = openai.Model.list()
    for model in response['data']:
        if 'gpt' in model['id']:
            tempmodels.append(model['id'])
            
    return gr.Dropdown.update(choices=tempmodels,interactive=True,value=tempmodels[0])

transcription_out = gr.Textbox(label="文字起こし結果")
presummary_prompt = """
あなたは、プロの要約作成者です。
以下の制約条件、内容を元に要点をまとめてください。
# 制約条件
・要点をまとめ、簡潔に書いて下さい。
・誤字・脱字があるため、話の内容を予測して置き換えてください。     
"""

summary_prompt = """
あなたは、プロの議事録作成者です。
以下の制約条件、内容を元に要点をまとめ、議事録を作成してください。
# 制約条件
・要点をまとめ、簡潔に書いて下さい。
・誤字・脱字があるため、話の内容を予測して置き換えてください。
・見やすいフォーマットにしてください。
・決まったこと、決めたことについては明確に記載してください。次のアクションがわからないと困ります。  
"""

api_key_String =  os.environ.get("OPEN_AI_APIKEY")
openai.api_key = api_key_String
tempmodels = []
response = openai.Model.list()
for model in response['data']:
    if 'gpt' in model['id']:
        tempmodels.append(model['id'])

with gr.Blocks() as inter:
    caption = gr.Markdown(
        """
        ##### 動画や音声を元に会議録を自動生成するためのアプリです。
        ##### 音声ファイルがおすすめです。ファイルの容量は軽い方が良いです
        """
    )
    with gr.Column():
        api_key = gr.Textbox(label="APIキー",value=api_key_String,interactive=True,visible=False)
        # api_button = gr.Button(value="APIキーを確認する", type="button")
        api_list = gr.Dropdown(label="モデル", choices=tempmodels,interactive=True,value="Modelを選択してください")
        # api_button.click(get_available_models, inputs=[api_key],outputs=api_list)
    with gr.Row():
        with gr.Row():
            pre_summary_text =gr.Textbox(label="要約を作成する前処理用のプロンプト",interactive=True,value=presummary_prompt)
            summary_text =gr.Textbox(label="要約を作成する用のプロンプト",interactive=True,value=summary_prompt)
    with gr.Column():
        file = gr.File(label="動画ファイル")
        excute_Button = gr.Button(value="実行", type="button")    
        excute_Button.click(transcription_excute, [api_key,file,api_list],transcription_out)
    with gr.Column():
        transcription_out.render()
        pre_summary_out = gr.Textbox(label="前処理結果")
        summary_out = gr.Textbox(label="議事録データ")
        transcription_out.change(pre_summary_excute, [api_key,api_list,transcription_out,pre_summary_text],pre_summary_out)
        pre_summary_out.change(summary_excute, [api_key,api_list,pre_summary_out,summary_text],summary_out)
        
app = FastAPI()
app = gr.mount_gradio_app(app, inter,path="/")