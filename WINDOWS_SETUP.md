# Windows Server Setup Guide - 24/7 Running with Clean URLs

This guide will set up your Drop List application on Windows Server to:
- Run 24/7 automatically (even after server reboots)
- Use clean URLs without port numbers (e.g., `http://192.168.1.100` instead of `http://192.168.1.100:8000`)

---

## Prerequisites

Before starting, ensure you have:
1. **Windows Server 2016 or later** (or Windows 10/11 Pro)
2. **Administrator access** to the server
3. **Python 3.10 or higher** - Download from https://python.org/downloads/
4. **ODBC Driver 18 for SQL Server** - Download from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## Option 1: Automated Setup (Recommended - Easy!)

### Step 1: Copy files to the server

Transfer your entire project folder to the Windows server using:
- Remote Desktop (copy/paste)
- Network share
- USB drive
- Git clone

### Step 2: Run the setup script

1. Open **PowerShell as Administrator**
   - Press Windows key, type "PowerShell"
   - Right-click "Windows PowerShell"
   - Select "Run as Administrator"

2. Navigate to your project folder:
   ```powershell
   cd "C:\path\to\Drop List"
   ```

3. Allow script execution (one-time only):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. Run the setup script:
   ```powershell
   .\setup-windows.ps1
   ```

The script will:
- Check Python and ODBC driver installation
- Create virtual environment and install dependencies
- Download and install NSSM (service manager)
- Create Windows service for 24/7 operation
- Install and configure IIS as reverse proxy
- Configure Windows Firewall
- Start everything automatically

**That's it!** Once complete, your app will be accessible at `http://YOUR-SERVER-IP`

---

## Option 2: Manual Setup

If you prefer to set up manually or troubleshoot:

### Step 1: Install Prerequisites

1. **Install Python 3.10+**
   - Download from https://python.org/downloads/
   - **IMPORTANT**: Check "Add Python to PATH" during installation
   - Verify: Open Command Prompt and type `python --version`

2. **Install ODBC Driver 18 for SQL Server**
   - Download from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
   - Install with default settings

### Step 2: Set Up Application

Open **PowerShell as Administrator**:

```powershell
# Create application directory
New-Item -ItemType Directory -Force -Path "C:\inetpub\drop-list"

# Copy your files to this directory
Copy-Item -Path "C:\path\to\your\files\*" -Destination "C:\inetpub\drop-list" -Recurse

# Navigate to the directory
cd C:\inetpub\drop-list

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Test the Application

```powershell
# Still in C:\inetpub\drop-list with venv activated
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open browser and test: `http://localhost:8000`

If it works, press `Ctrl+C` to stop and continue to the next step.

### Step 4: Install NSSM (Service Manager)

```powershell
# Create directory for NSSM
New-Item -ItemType Directory -Force -Path "C:\nssm"

# Download NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"

# Extract
Expand-Archive -Path "$env:TEMP\nssm.zip" -DestinationPath $env:TEMP -Force

# Copy to C:\nssm (use win64 for 64-bit Windows)
Copy-Item "$env:TEMP\nssm-2.24\win64\nssm.exe" "C:\nssm\" -Force
```

### Step 5: Create Windows Service

```powershell
# Install the service
C:\nssm\nssm.exe install DropListApp "C:\inetpub\drop-list\venv\Scripts\python.exe" "-m uvicorn main:app --host 127.0.0.1 --port 8000"

# Set working directory
C:\nssm\nssm.exe set DropListApp AppDirectory "C:\inetpub\drop-list"

# Set display name and description
C:\nssm\nssm.exe set DropListApp DisplayName "Drop List Web Application"
C:\nssm\nssm.exe set DropListApp Description "FastAPI web application for Drop List management"

# Set to start automatically
C:\nssm\nssm.exe set DropListApp Start SERVICE_AUTO_START

# Set log files
C:\nssm\nssm.exe set DropListApp AppStdout "C:\inetpub\drop-list\service.log"
C:\nssm\nssm.exe set DropListApp AppStderr "C:\inetpub\drop-list\service_error.log"

# Start the service
C:\nssm\nssm.exe start DropListApp

# Check status
Get-Service DropListApp
```

### Step 6: Install and Configure IIS

#### Install IIS:

```powershell
# Install IIS with management tools
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
```

#### Install URL Rewrite Module:

1. Download from: https://www.iis.net/downloads/microsoft/url-rewrite
2. Run the installer (rewrite_amd64_en-US.msi)

#### Install Application Request Routing (ARR):

1. Download from: https://www.iis.net/downloads/microsoft/application-request-routing
2. Run the installer (requestRouter_amd64.msi)

#### Enable ARR Proxy:

```powershell
# Enable proxy functionality
Import-Module WebAdministration
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"
```

#### Create IIS Website:

```powershell
# Create website directory
New-Item -ItemType Directory -Force -Path "C:\inetpub\wwwroot\droplist"

# Stop default website
Stop-Website -Name "Default Web Site"

# Create web.config for reverse proxy
@"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
"@ | Out-File -FilePath "C:\inetpub\wwwroot\droplist\web.config" -Encoding UTF8

# Create website
New-Website -Name "DropList" -PhysicalPath "C:\inetpub\wwwroot\droplist" -Port 80

# Start website
Start-Website -Name "DropList"
```

### Step 7: Configure Windows Firewall

```powershell
# Allow HTTP traffic
New-NetFirewallRule -DisplayName "Drop List - HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

---

## Verify Everything is Working

```powershell
# Check service status
Get-Service DropListApp

# Check IIS website
Get-Website

# View application logs
Get-Content C:\inetpub\drop-list\service.log -Tail 20

# Get server IP address
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" }
```

Then from another computer on the company network, open a browser and go to:
**http://YOUR-SERVER-IP**

---

## Managing the Application

### Service Management:

```powershell
# Check status
Get-Service DropListApp

# Start service
Start-Service DropListApp

# Stop service
Stop-Service DropListApp

# Restart service
Restart-Service DropListApp

# View logs
Get-Content C:\inetpub\drop-list\service.log -Tail 50 -Wait  # Real-time logs
Get-Content C:\inetpub\drop-list\app.log -Tail 50           # Application logs
```

### IIS Management:

```powershell
# Check website status
Get-Website -Name "DropList"

# Restart IIS
iisreset

# Start/Stop website
Start-Website -Name "DropList"
Stop-Website -Name "DropList"
```

### Updating the Application:

```powershell
# Stop the service
Stop-Service DropListApp

# Navigate to app directory
cd C:\inetpub\drop-list

# Pull new changes or copy new files
# If using git:
git pull

# Restart the service
Start-Service DropListApp
```

---

## Troubleshooting

### Service won't start:

```powershell
# Check service status and errors
Get-Service DropListApp
Get-Content C:\inetpub\drop-list\service_error.log -Tail 50

# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Verify Python and dependencies
cd C:\inetpub\drop-list
.\venv\Scripts\Activate.ps1
python --version
pip list
```

### Can't access from other computers:

```powershell
# Check Windows Firewall
Get-NetFirewallRule -DisplayName "*Drop List*"

# Check IIS is running
Get-Service W3SVC
Get-Website

# Test locally first
Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing

# Check server IP
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" }
```

### IIS shows 500 or 502 error:

- Make sure the Python service is running: `Get-Service DropListApp`
- Check ARR proxy is enabled
- Verify web.config is correct
- Check IIS logs: `C:\inetpub\logs\LogFiles`

### Database connection errors:

```powershell
# Verify .env file exists and has correct credentials
Get-Content C:\inetpub\drop-list\.env

# Test Azure SQL connectivity
Test-NetConnection -ComputerName vintechpicklist.database.windows.net -Port 1433

# Make sure Azure SQL firewall allows your server's public IP
```

---

## Alternative: Run Without IIS (Simpler but less professional)

If you don't want to use IIS, you can run the app directly on port 80:

1. Modify the service to use port 80:
   ```powershell
   C:\nssm\nssm.exe set DropListApp AppParameters "-m uvicorn main:app --host 0.0.0.0 --port 80"
   C:\nssm\nssm.exe restart DropListApp
   ```

2. Configure firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "Drop List - Port 80" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
   ```

Users can then access via: `http://YOUR-SERVER-IP` (no IIS needed)

**Note**: Running on port 80 requires administrator privileges and prevents using IIS for other sites.

---

## What Each Component Does

- **Python Virtual Environment** (`venv`) - Isolated Python packages
- **NSSM** - Makes the app run as a Windows Service (24/7, auto-start on boot)
- **IIS** - Web server that provides clean URLs and better performance
- **URL Rewrite** - IIS module for reverse proxy rules
- **ARR** - IIS module for proxying requests to the Python app
- **Windows Service** - Keeps app running even after reboot

---

## Architecture Overview

```
User's Browser
    ↓
http://server-ip (port 80)
    ↓
IIS (reverse proxy)
    ↓
http://127.0.0.1:8000 (internal)
    ↓
Windows Service (DropListApp)
    ↓
Your FastAPI App (Uvicorn)
    ↓
Azure SQL Database
```

Benefits:
- IIS handles SSL, compression, static files
- Application runs as Windows Service
- Users access via clean URL on port 80
- Service auto-starts on boot and restarts if it crashes

---

## Next Steps

1. Test accessing from multiple devices on company WiFi
2. Consider adding HTTPS with SSL certificate
3. Set up regular backups of Azure SQL database
4. Monitor logs regularly for errors
5. Create a simple batch file for common operations

For more details, see `DEPLOYMENT_GUIDE.md`
