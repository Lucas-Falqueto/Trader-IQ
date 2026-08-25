@echo off
title Bot IQ Option - Pullback (Portfolio)
color 0A

echo ========================================================
echo         INICIANDO PORTFOLIO DE ROBOS (MONTECARLO)       
echo ========================================================
echo.

:: Ativa o ambiente virtual local se existir
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Ambiente virtual nao encontrado. Usando Python global.
)

echo.
echo Pressione CTRL+C a qualquer momento para desligar os robos.
echo.

:: Inicia o gerenciador de processos
python bots\run_all.py

echo.
pause
