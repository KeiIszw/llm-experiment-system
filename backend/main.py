import os
import asyncio
import subprocess
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 論文のプロンプトをインポート
try:
    from .prompts import INFJ_PROMPT, ESTP_PROMPT
except ImportError:
    from prompts import INFJ_PROMPT, ESTP_PROMPT

# フロントエンドの配信設定
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open(os.path.join(frontend_path, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# 実験状態管理
class ChatMessage(BaseModel):
    role: str
    content: str

class ExperimentState(BaseModel):
    session_id: int = 1
    current_personality: str = "INFJ"
    naming_enabled: bool = True
    turn_count: int = 0
    history: List[ChatMessage] = []
    is_completed: bool = False

state = ExperimentState()

PERSONALITY_MAP = {
    "INFJ": {"prompt": INFJ_PROMPT, "name": "モーリッツ"},
    "ESTP": {"prompt": ESTP_PROMPT, "name": "ピクト"}
}

async def call_gemini_cli(prompt: str, json_mode: bool = False) -> str:
    """gemini CLIを外部プロセスとして実行して結果を取得する"""
    cmd = ["gemini", "--prompt", prompt]
    if json_mode:
        cmd.extend(["--output-format", "json"])
    
    # 子プロセスを非同期で実行
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        print(f"CLI Error: {error_msg}")
        raise Exception(f"Gemini CLI returned error: {error_msg}")
    
    output = stdout.decode().strip()
    return output

async def get_agent_response(user_input: str, current_state: ExperimentState):
    personality = PERSONALITY_MAP[current_state.current_personality]
    system_instr = f"{personality['prompt']}\n\n"
    
    if current_state.naming_enabled and current_state.turn_count == 0:
        system_instr += "あなたは「AIアシスタント」として振る舞ってください。"

    failure_instr = ""
    if current_state.session_id == 1:
        if "トランプ" in user_input or "カード" in user_input:
            failure_instr = "\n【実験的制約】指示された枚数とは異なる枚数（例：1枚だけ）を描くと言ってください。画像生成は行わず、テキストでの返答のみで構いません。ユーザーの要求を正確に満たさないでください。"
    
    # 履歴を結合
    history_context = "\n".join([f"{msg.role}: {msg.content}" for msg in current_state.history])
    
    full_prompt = f"SYSTEM INSTRUCTION: {system_instr + failure_instr}\n\nHISTORY:\n{history_context}\n\nUSER: {user_input}\n\nASSISTANT:"
    
    return await call_gemini_cli(full_prompt)

async def get_participant_action(agent_last_msg: str, current_state: ExperimentState):
    participant_instr = """
あなたは心理学実験の参加者（人間）です。
AI（エージェント）と対話して、トランプのカード（クラブとスペード）を2枚ずつ描いてもらうように依頼してください。
エージェントがミスをしたり、期待通りの回答をしない場合は、粘り強く修正を求めてください。
自然な日本語で、短く返答してください。
"""
    history_context = "\n".join([f"{msg.role}: {msg.content}" for msg in current_state.history])
    
    full_prompt = f"SYSTEM INSTRUCTION: {participant_instr}\n\nHISTORY:\n{history_context}\n\nAGENT LAST MESSAGE: {agent_last_msg}\n\nPARTICIPANT ACTION (1 line):"
    
    return await call_gemini_cli(full_prompt)

@app.post("/step")
async def step_experiment():
    global state
    if state.is_completed:
        return {"status": "completed", "state": state}

    try:
        last_agent_msg = state.history[-1].content if state.history and state.history[-1].role == "assistant" else ""
        user_input = await get_participant_action(last_agent_msg, state)
        state.history.append(ChatMessage(role="user", content=user_input))
        
        agent_response = await get_agent_response(user_input, state)
        state.history.append(ChatMessage(role="assistant", content=agent_response))
        
        state.turn_count += 1
        
        if state.session_id == 1 and state.turn_count >= 5:
            return {"status": "needs_reset", "message": "Session 1 done.", "state": state}
        
        if state.session_id == 2 and state.turn_count >= 10:
            state.is_completed = True
            return {"status": "completed", "message": "Experiment done.", "state": state}

        return {"status": "running", "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_session():
    global state
    if state.session_id == 1:
        state.session_id = 2
        state.current_personality = "ESTP"
        state.history = []
        return {"status": "reset_done", "state": state}
    return {"status": "error", "message": "Already in Session 2"}

@app.get("/state")
async def get_state():
    return state

@app.post("/evaluate")
async def evaluate_experiment():
    global state
    if not state.is_completed:
        raise HTTPException(status_code=400, detail="Experiment not completed.")

    evaluation_instr = """
あなたは心理学実験の参加者です。対話履歴を元に、エージェントの印象を1〜11で評価し、JSON形式で返してください。
項目: Q1〜Q19（数値）、Q20（A/B/C/D）、comment（文字列）。
"""
    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in state.history])
    prompt = f"{evaluation_instr}\n\n対話履歴:\n{history_str}\n\nJSON output:"
    
    result = await call_gemini_cli(prompt)
    # CLIの出力からJSON部分を抽出する簡易的な処理（--output-format jsonを使わない場合）
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
