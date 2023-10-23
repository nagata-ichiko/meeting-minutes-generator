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

def convert_mp4_to_mp3(mp4_file_path,file_name):
    mp3_file_path = os.path.splitext(file_name)[0] + '.mp3'
    audio = mp.AudioFileClip(mp4_file_path)
    audio.write_audiofile(mp3_file_path)
    return mp3_file_path

def transcribe_audio(mp3_file_path):
    with open(mp3_file_path, 'rb') as audio_file:
        transcription = openai.Audio.transcribe("whisper-1", audio_file, language='ja')

    return transcription.text

#テキストを保存
def save_text_to_file(text, output_file_path):
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(text)

#mp3ファイルを分割し、保存し、ファイルリストを返す
def split_audio(mp3_file_path, interval_ms, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    audio = AudioSegment.from_file(mp3_file_path)
    file_name, ext = os.path.splitext(os.path.basename(mp3_file_path))

    mp3_file_path_list = []

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

    #音声ファイルリストを出力
    return mp3_file_path_list

def excute(api_key, mp4_file_path,model):
    openai.api_key = api_key
    if model not in get_available_models(api_key):
        return "エラー：使用できないモデルです。","エラー：使用できないモデルです。"

    file_path = mp4_file_path.name
    file_name = mp4_file_path.name.split("/")[-1]
    mp3_file_path = convert_mp4_to_mp3(file_path,file_name)

    output_folder = "./output/"
    interval_ms = 480_000 # 60秒 = 60_000ミリ秒

    mp3_file_path_list = split_audio(mp3_file_path, interval_ms, output_folder)
    transcription_list = []
    for mp3_file_path in mp3_file_path_list:
        transcription = transcribe_audio(mp3_file_path)
        transcription_list.append(transcription)
        output_file_path = os.path.splitext(mp3_file_path)[0] + '_transcription.txt'
    
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


    print("議事録を作成中です...")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.0,
    )
    output_row_file_path = output_folder + '_RowData.txt'
    output_file_path = output_folder + '_mitunes.txt'
    save_text_to_file(response['choices'][0]['message']['content'], output_file_path)
    save_text_to_file(pre_summary, output_row_file_path)
    return transcription_list,response['choices'][0]['message']['content']
    
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
    fn=excute,
    live=True,
    ).launch(server_name = "0.0.0.0", server_port=7860, share=True)