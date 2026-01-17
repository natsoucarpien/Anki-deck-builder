@echo off
cd /d "%~dp0"

echo ============================================================
echo   LearnableMeta to Anki Deck Builder
echo ============================================================
echo.

set /p URL="Entrez l'URL du deck LearnableMeta: "

if "%URL%"=="" (
    echo.
    echo Erreur: Aucune URL fournie.
    pause
    exit /b 1
)

echo.
python learnablemeta_to_anki.py "%URL%"

echo.
pause
