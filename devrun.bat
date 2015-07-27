@echo off
python gmnoty.pyw %*
if %ERRORLEVEL% NEQ 0 (
	pause
)