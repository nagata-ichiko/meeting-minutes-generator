# meeting-minutes-generator

このリポジトリは動画や音声を元に会議録を自動生成するためのプログラムです。

#　使い方

- このリポジトリをクローンしてください。
- 以下のコマンドを実行してください。

```
pip install -r requirements.txt
```

- 以下のコマンドを実行してください。

```
python local.py
```

- OpenAI の API キーを入力してください。
- GPT のモデルを選択してください。
- ファイルを選択してください。

# その他

- main.py は Render デプロイ用のファイルです。
- Docker は Gradio の仕様によって正常に動作しない場合があります。
- Render などにデプロイした場合、Gradio の仕様によって正常に動作しない場合があります。
- 正常に動作しない場合は Pythin ファイルを直接実行してください。
- Main.py は以下のコマンドで実行できます。

```
uvicorn main:app --host 0.0.0.0
```

- local.py はローカル実行用のファイルです。
- docker compose でも実行できます。実行されるのは Main.py です。local の方は Docker だと動作しません(Gradio の仕様)。
- 本アプリでは、文字起こし結果と要約を出力します。Main.py は文字起こしと要約を結合して出力します。local.py は文字起こしと要約を別々に出力します。ちょっとみやすい。
