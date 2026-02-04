@echo off
echo Copying resumes to project...
echo.

cd /d "%~dp0"

set SOURCE=C:\Users\karas\OneDrive\Desktop\tes\bullet\W2\resumes_latex
set DEST=D:\Projects\resume-rag\data\resumes

if not exist "%DEST%" mkdir "%DEST%"

echo Copying from: %SOURCE%
echo Copying to: %DEST%
echo.

xcopy "%SOURCE%\*.tex" "%DEST%\" /Y /S
xcopy "%SOURCE%\Software_Engineer\*.tex" "%DEST%\Software_Engineer\" /Y /I
xcopy "%SOURCE%\Security_Engineer\*.tex" "%DEST%\Security_Engineer\" /Y /I
xcopy "%SOURCE%\DevOps_SRE\*.tex" "%DEST%\DevOps_SRE\" /Y /I
xcopy "%SOURCE%\Data_AI\*.tex" "%DEST%\Data_AI\" /Y /I
xcopy "%SOURCE%\Specialized\*.tex" "%DEST%\Specialized\" /Y /I

echo.
echo Done! Now run: python main.py index
pause
