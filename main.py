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

def excute(api_key, mp4_file_path,model):
    print("処理を開始します...")
    openai.api_key = api_key
    if model not in get_available_models(api_key):
        return "エラー：使用できないモデルです。","エラー：使用できないモデルです。"
    
    print("mp4ファイルをmp3に変換しています...")
    mp3_file_path = os.path.splitext(mp4_file_path.name.split("/")[-1])[0] + '.mp3'
    audio = mp.AudioFileClip(mp4_file_path.name)
    print("変換が完了しました。ファイルを作成します...")
    audio.write_audiofile(mp3_file_path)
    
    output_folder = "./output/"
    interval_ms = 480_000 # 60秒 = 60_000ミリ秒

    print("outputフォルダを作成します...")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    print("Audioファイルを取得します...")
    audio = AudioSegment.from_file(mp3_file_path)
    print("分割用のファイル名を取得します...")
    file_name, ext = os.path.splitext(os.path.basename(mp3_file_path))

    mp3_file_path_list = []

    print("音声ファイルを分割しています...")
    n_splits = len(audio) // interval_ms
    for i in range(n_splits + 1):
        #開始、終了時間
        start = i * interval_ms
        end = (i + 1) * interval_ms
        #分割
        split = audio[start:end]
        #出力ファイル名
        output_file_name = output_folder + os.path.splitext(mp3_file_path)[0] + "_" + str(i) + ".mp3"
        #出力
        split.export(output_file_name, format="mp3")

        #音声ファイルリストに追加
        mp3_file_path_list.append(output_file_name)
    
    transcription_list = []
    for mp3_file_path in mp3_file_path_list:
        transcription = ""
        print("文字起こしをしています...")
        with open(mp3_file_path, 'rb') as audio_file:
            transcription = openai.Audio.transcribe("whisper-1", audio_file, language='ja')
        transcription_list.append(transcription.text)
        output_file_path = output_folder + '_transcription.txt'
    
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
    output_row_file_path = output_folder + '_RowData.txt'
    output_file_path = output_folder + '_mitunes.txt'
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(response['choices'][0]['message']['content'])
        
    with open(output_row_file_path, 'w', encoding='utf-8') as f:
        transcriptions_str = "\n".join(transcription_list)
        f.write(transcriptions_str)
    # return transcription_list,response['choices'][0]['message']['content']
    return response['choices'][0]['message']['content']
    
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

with gr.Blocks() as io:
    with gr.Row():
        with gr.Column():
            api_key = gr.inputs.Textbox(label="APIキー")
            # api_button = gr.Button(label="APIキーを確認", type="button")
            api_list = gr.inputs.Dropdown(label="モデル", choices=models)
            file = gr.inputs.File(label="動画ファイル")
            excute_Button = gr.Button(label="実行", type="button")
            excute_Button.click(excute, [api_key, file, api_list], meeting)      
            # excute_Button.click(excute, [api_key, file, api_list], [rowdata, meeting])      
        with gr.Column():
            # rowdata.render()
            meeting.render()



# io = gr.Interface(title="テキストとファイルの入力",description="テキストとファイルを入力して処理を実行します。",
#     inputs=[
#         gr.inputs.Textbox(label="APIキー"),
#         gr.inputs.File(label="動画ファイル"),
#         gr.inputs.Dropdown(label="モデル",choices=models),
#     ],
#     outputs=[
#         gr.outputs.Textbox(label="文字起こしデータ"),
#         gr.outputs.Textbox(label="議事録データ"),
#     ],
#     fn=excute,
#     )
        
app = FastAPI()
app = gr.mount_gradio_app(app, io,path="/")
# app.launch(server_name = "0.0.0.0", server_port=7860,share=True,debug=True)
