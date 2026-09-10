@echo off
REM Thin Windows shim so `make <target>` works without GNU make.
setlocal
set PY=python
if "%1"=="" goto help
if "%1"=="setup"    ( %PY% -m pip install -r requirements.txt & goto :eof )
if "%1"=="data"     ( %PY% -m data.generate & goto :eof )
if "%1"=="train"    ( %PY% -m models.train & goto :eof )
if "%1"=="optimise" ( %PY% -m optimiser.run_demo & goto :eof )
if "%1"=="app"      ( %PY% -m streamlit run app/streamlit_app.py & goto :eof )
if "%1"=="eval"     ( %PY% -m eval.run_golden & %PY% -m eval.regression_suite & goto :eof )
if "%1"=="feedback" ( %PY% -m eval.feedback_retrain & goto :eof )
:help
echo targets: setup ^| data ^| train ^| optimise ^| app ^| eval ^| feedback
endlocal
