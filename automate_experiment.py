import httpx
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def log(msg):
    print(f"[*] {msg}")

async def run_experiment():
    # タイムアウトをNoneにして長時間実行に対応
    async with httpx.AsyncClient(timeout=None) as client:
        log("実験シミュレーションを開始（または再開）します。")
        
        while True:
            try:
                # 状態を確認
                res = await client.get(f"{BASE_URL}/state")
                state = res.json()
                
                if state["is_completed"]:
                    log("実験がすべて完了しました。")
                    break
                
                # ステップ実行
                log(f"ステップ実行中... (Session {state['session_id']}, Turn {state['turn_count']})")
                res = await client.post(f"{BASE_URL}/step")
                data = res.json()
                
                if data["status"] == "needs_reset":
                    log("セッション1終了。リセットと人格切替を実行します。")
                    await client.post(f"{BASE_URL}/reset")
                    log("リセット完了。次のセッションを開始します。")
                
                elif data["status"] == "completed":
                    log("全ステップが終了しました。")
                    break
                
                time.sleep(1) # インターバル
            
            except Exception as e:
                log(f"エラーが発生しました（リトライします）: {e}")
                time.sleep(5)

        log("最終アンケート評価を取得します...")
        try:
            res = await client.post(f"{BASE_URL}/evaluate")
            print("\n--- 参加者LLMによる評価結果 ---")
            print(res.text)
        except Exception as e:
            log(f"評価の取得に失敗しました: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_experiment())
