@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Language Server Wrapper for GLM 5.2 via OpenRouter
REM ═══════════════════════════════════════════════════════════════
REM  This wrapper launches the real Antigravity language server
REM  with flags that redirect inference to our local proxy.
REM
REM  IMPORTANT: The proxy (openrouter_proxy.py) must be running
REM  on localhost:8741 BEFORE starting the IDE.
REM ═══════════════════════════════════════════════════════════════

set "REAL_LS=C:\Users\mahmo\AppData\Local\Programs\Antigravity IDE\resources\app\extensions\antigravity\bin\language_server_windows_x64.exe"

"%REAL_LS%" --inference_api_server_url=http://127.0.0.1:8741 --override_model_name=z-ai/glm-5.2 %*
