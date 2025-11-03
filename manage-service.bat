@echo off
REM Drop List Service Management Script
REM Run this as Administrator

echo ========================================
echo Drop List Service Management
echo ========================================
echo.
echo 1. Check Status
echo 2. Start Service
echo 3. Stop Service
echo 4. Restart Service
echo 5. View Logs (Last 20 lines)
echo 6. View Logs (Real-time)
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto logs_live
if "%choice%"=="7" goto end
goto invalid

:status
echo.
echo Checking service status...
powershell -Command "Get-Service DropListApp | Format-List"
echo.
echo IIS Website status:
powershell -Command "Get-Website -Name DropList | Format-List"
goto end

:start
echo.
echo Starting service...
net start DropListApp
echo.
echo Starting IIS website...
powershell -Command "Start-Website -Name DropList"
echo Service started!
goto end

:stop
echo.
echo Stopping service...
net stop DropListApp
echo Service stopped!
goto end

:restart
echo.
echo Restarting service...
net stop DropListApp
timeout /t 2 /nobreak > nul
net start DropListApp
echo.
echo Restarting IIS...
iisreset /restart
echo Service restarted!
goto end

:logs
echo.
echo Last 20 log lines:
echo ========================================
powershell -Command "Get-Content C:\inetpub\drop-list\service.log -Tail 20"
goto end

:logs_live
echo.
echo Showing real-time logs (Press Ctrl+C to stop)...
echo ========================================
powershell -Command "Get-Content C:\inetpub\drop-list\service.log -Tail 20 -Wait"
goto end

:invalid
echo Invalid choice. Please run the script again.
goto end

:end
echo.
pause
