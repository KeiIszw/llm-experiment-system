# LLM人格切替実験シミュレーションシステム

本プロジェクトは、論文「大規模言語モデルにおける人格切り替えがユーザの印象に与える影響」に基づき、人間の参加者をLLMで代用して実験を自動遂行するシステムです。

## プロジェクト概要
このシステムは、論文で提案された「人格切替システム」を持つAIエージェントと、人間の代わりに実験に参加する「参加者LLM」の対話をシミュレートします。
実験は2つのセッションで構成され、セッション1の終了時にエージェントの人格が切り替わります。最終的に、参加者LLMによるエージェントの印象評価（Q1〜Q20）をJSON形式で出力します。

## システム構成
- **Frontend**: 一般的なAIチャットツールを模したUI。人格情報を隠蔽し、純粋な対話画面として機能します。
- **Backend**: FastAPIを使用。Gemini APIの代わりに `gemini` CLIをサブプロセスとして呼び出すことで、安定した動作と認証情報の共有を実現しています。
- **Automation**: `automate_experiment.py` がAPIを介して実験手順（発話、リセット、評価）を自動制御します。

## 動作要件
- **Python 3.10以上**
- **uv**: Pythonパッケージ・プロジェクト管理ツール ([インストールガイド](https://docs.astral.sh/uv/getting-started/installation/))
- **Gemini CLI**: `gemini` コマンドが実行可能な環境。

## セットアップ

### 1. プロジェクトの準備
リポジトリ（またはフォルダ）に移動し、依存関係をインストールします。

```bash
cd llm-experiment-system
uv sync
```

### 2. APIキーの設定
Gemini CLIが動作するために必要なAPIキーを設定します。

- **Windows (コマンドプロンプト)**:
  ```cmd
  set GOOGLE_API_KEY=your_api_key_here
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:GOOGLE_API_KEY="your_api_key_here"
  ```
- **macOS / Linux**:
  ```bash
  export GOOGLE_API_KEY='your_api_key_here'
  ```

## 実行方法

### ステップ1: サーバーの起動
まず、WebアプリおよびAPIサーバーを起動します。

```bash
uv run python -m backend.main
```
起動後、ブラウザで `http://localhost:8000` を開くと、シミュレーション中の画面をリアルタイムで確認できます。

### ステップ2: 実験の自動実行
サーバーを起動したまま、**別のターミナル**を開き、以下のスクリプトを実行します。

```bash
cd llm-experiment-system
uv run automate_experiment.py
```
これにより、参加者LLMが自動的に対話を開始し、セッションリセット、人格切替、最終アンケート回答までを完遂します。

## 開発プロンプトログ
本システムを作成するために使用された一連のプロンプトです。

1. `./lib/thesis25_nishizawa_260319.pdfの研究で行われている実験において，人間の参加者の代わりに，LLMで代用して実験を行いたい．まず，論文記載のLLM人格切替システムを実装したチャットシミュレーションシステムをwebアプリとして実装し，LLMが実験に参加するシステムをpythonで作成せよ．ただしpythonの実行環境にはuvを使用せよ．`
2. `フロントエンドに人格切替を行うという内容を含まないようにして．普通のAIチャットツールのようにして．また，LLMの参加者はgemini CLIがGUIを操作して実験を行うようにして．`
3. `openaiのapiキーではなく，gemini 2.5 flashを使用するように変更して`
4. `gemini apiが不安定なので，gemini CLIを使うのはどうか`
5. `本プロジェクトにREADME.mdを追加して．mac以外のpcでも使い方がわかるように記述して．加えて，本実験システムを作成するために私が送ったプロンプトもメモしておいて．`
