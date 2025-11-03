# Drop List Web App - Windows Server Setup Script
# Run this as Administrator in PowerShell

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Please run this script as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Drop List Application Setup for Windows" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$APP_DIR = "C:\inetpub\drop-list"
$SCRIPT_DIR = $PSScriptRoot

# Step 1: Check Python
Write-Host "Step 1: Checking Python installation..." -ForegroundColor Green
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Gray

    # Check version is 3.10 or higher
    $version = [regex]::Match($pythonVersion, "(\d+)\.(\d+)").Groups
    $major = [int]$version[1].Value
    $minor = [int]$version[2].Value

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Host "WARNING: Python 3.10 or higher is recommended. You have Python $major.$minor" -ForegroundColor Yellow
        Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne 'y') { exit }
    }
} catch {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    pause
    exit
}

# Step 2: Check ODBC Driver
Write-Host ""
Write-Host "Step 2: Checking ODBC Driver for SQL Server..." -ForegroundColor Green
$odbcDrivers = Get-OdbcDriver | Where-Object { $_.Name -like "*SQL Server*" }
if ($odbcDrivers) {
    Write-Host "Found ODBC drivers for SQL Server" -ForegroundColor Gray
} else {
    Write-Host "WARNING: ODBC Driver 18 for SQL Server not found" -ForegroundColor Yellow
    Write-Host "Download from: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') { exit }
}

# Step 3: Copy application files
Write-Host ""
Write-Host "Step 3: Setting up application directory..." -ForegroundColor Green
if (Test-Path $APP_DIR) {
    $backup = "${APP_DIR}_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "Backing up existing installation to $backup" -ForegroundColor Yellow
    Move-Item $APP_DIR $backup
}

New-Item -ItemType Directory -Force -Path $APP_DIR | Out-Null
Copy-Item -Path "$SCRIPT_DIR\*" -Destination $APP_DIR -Recurse -Force
Set-Location $APP_DIR
Write-Host "Application files copied to $APP_DIR" -ForegroundColor Gray

# Step 4: Create virtual environment
Write-Host ""
Write-Host "Step 4: Creating Python virtual environment..." -ForegroundColor Green
python -m venv venv
if (-not $?) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    pause
    exit
}

# Activate venv and install dependencies
Write-Host "Installing Python dependencies (this may take a few minutes)..." -ForegroundColor Gray
& "$APP_DIR\venv\Scripts\pip.exe" install --upgrade pip
& "$APP_DIR\venv\Scripts\pip.exe" install -r requirements.txt
if (-not $?) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    pause
    exit
}
Write-Host "Dependencies installed successfully" -ForegroundColor Gray

# Step 5: Download and setup NSSM
Write-Host ""
Write-Host "Step 5: Setting up Windows Service (NSSM)..." -ForegroundColor Green
$nssmPath = "C:\nssm"
$nssmExe = "$nssmPath\nssm.exe"

if (-not (Test-Path $nssmExe)) {
    Write-Host "Downloading NSSM (Non-Sucking Service Manager)..." -ForegroundColor Gray
    $nssmZip = "$env:TEMP\nssm.zip"

    try {
        Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force

        # Copy the appropriate architecture version
        if ([Environment]::Is64BitOperatingSystem) {
            Copy-Item "$env:TEMP\nssm-2.24\win64\nssm.exe" $nssmPath -Force
        } else {
            Copy-Item "$env:TEMP\nssm-2.24\win32\nssm.exe" $nssmPath -Force
        }

        Remove-Item $nssmZip -Force
        Write-Host "NSSM installed to $nssmPath" -ForegroundColor Gray
    } catch {
        Write-Host "ERROR: Failed to download NSSM" -ForegroundColor Red
        Write-Host "Please download manually from https://nssm.cc/download and extract to C:\nssm" -ForegroundColor Yellow
        pause
        exit
    }
} else {
    Write-Host "NSSM already installed" -ForegroundColor Gray
}

# Remove existing service if it exists
$serviceName = "DropListApp"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    & $nssmExe stop $serviceName
    & $nssmExe remove $serviceName confirm
}

# Install the service
Write-Host "Installing Windows Service..." -ForegroundColor Gray
$pythonExe = "$APP_DIR\venv\Scripts\python.exe"
$appCommand = "-m uvicorn main:app --host 127.0.0.1 --port 8000"

& $nssmExe install $serviceName $pythonExe $appCommand
& $nssmExe set $serviceName AppDirectory $APP_DIR
& $nssmExe set $serviceName DisplayName "Drop List Web Application"
& $nssmExe set $serviceName Description "FastAPI web application for Drop List management"
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppStdout "$APP_DIR\service.log"
& $nssmExe set $serviceName AppStderr "$APP_DIR\service_error.log"

# Start the service
Write-Host "Starting service..." -ForegroundColor Gray
& $nssmExe start $serviceName
Start-Sleep -Seconds 3

$service = Get-Service -Name $serviceName
if ($service.Status -eq "Running") {
    Write-Host "Service started successfully!" -ForegroundColor Green
} else {
    Write-Host "WARNING: Service may not have started correctly" -ForegroundColor Yellow
    Write-Host "Status: $($service.Status)" -ForegroundColor Yellow
}

# Step 6: Setup IIS as reverse proxy
Write-Host ""
Write-Host "Step 6: Setting up IIS reverse proxy..." -ForegroundColor Green

# Check if IIS is installed
$iisFeature = Get-WindowsFeature -Name Web-Server -ErrorAction SilentlyContinue
if (-not $iisFeature -or -not $iisFeature.Installed) {
    Write-Host "IIS is not installed. Would you like to install it? (y/n)" -ForegroundColor Yellow
    $installIIS = Read-Host

    if ($installIIS -eq 'y') {
        Write-Host "Installing IIS... (this may take several minutes)" -ForegroundColor Gray
        Install-WindowsFeature -Name Web-Server -IncludeManagementTools
        Write-Host "IIS installed successfully" -ForegroundColor Green
    } else {
        Write-Host "Skipping IIS setup. You can access the app at http://localhost:8000" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To allow access from other computers, configure Windows Firewall:" -ForegroundColor Yellow
        Write-Host "  New-NetFirewallRule -DisplayName 'Drop List App' -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Setup Complete!" -ForegroundColor Green
        pause
        exit
    }
}

# Install URL Rewrite module (required for reverse proxy)
Write-Host "Checking for URL Rewrite module..." -ForegroundColor Gray
$rewriteModule = Get-WebGlobalModule -Name "IIS_UrlRewrite" -ErrorAction SilentlyContinue
if (-not $rewriteModule) {
    Write-Host "URL Rewrite module not found. Installing..." -ForegroundColor Yellow
    Write-Host "Downloading URL Rewrite module..." -ForegroundColor Gray

    $rewriteInstaller = "$env:TEMP\rewrite_amd64.msi"
    try {
        Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" -OutFile $rewriteInstaller

        Write-Host "Installing URL Rewrite module..." -ForegroundColor Gray
        Start-Process msiexec.exe -ArgumentList "/i `"$rewriteInstaller`" /quiet" -Wait
        Remove-Item $rewriteInstaller -Force

        Write-Host "URL Rewrite module installed" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to download/install URL Rewrite module" -ForegroundColor Red
        Write-Host "Please download manually from: https://www.iis.net/downloads/microsoft/url-rewrite" -ForegroundColor Yellow
    }
}

# Install ARR (Application Request Routing)
Write-Host "Checking for Application Request Routing..." -ForegroundColor Gray
$arrModule = Get-WebGlobalModule -Name "ApplicationRequestRouting" -ErrorAction SilentlyContinue
if (-not $arrModule) {
    Write-Host "ARR module not found. Installing..." -ForegroundColor Yellow
    Write-Host "Downloading ARR module..." -ForegroundColor Gray

    $arrInstaller = "$env:TEMP\ARR_amd64.msi"
    try {
        Invoke-WebRequest -Uri "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi" -OutFile $arrInstaller

        Write-Host "Installing ARR module..." -ForegroundColor Gray
        Start-Process msiexec.exe -ArgumentList "/i `"$arrInstaller`" /quiet" -Wait
        Remove-Item $arrInstaller -Force

        Write-Host "ARR module installed" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to download/install ARR module" -ForegroundColor Red
        Write-Host "Please download manually from: https://www.iis.net/downloads/microsoft/application-request-routing" -ForegroundColor Yellow
    }
}

# Enable ARR proxy
Import-Module WebAdministration
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"

# Create IIS website
Write-Host "Creating IIS website..." -ForegroundColor Gray
$siteName = "DropList"
$existingSite = Get-Website -Name $siteName -ErrorAction SilentlyContinue
if ($existingSite) {
    Remove-Website -Name $siteName
}

# Stop default website
Stop-Website -Name "Default Web Site" -ErrorAction SilentlyContinue

# Create web.config for reverse proxy
$webConfigContent = @"
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
        <httpProtocol>
            <customHeaders>
                <add name="X-Forwarded-For" value="{REMOTE_ADDR}" />
            </customHeaders>
        </httpProtocol>
    </system.webServer>
</configuration>
"@

$iisRoot = "C:\inetpub\wwwroot\droplist"
New-Item -ItemType Directory -Force -Path $iisRoot | Out-Null
$webConfigContent | Out-File -FilePath "$iisRoot\web.config" -Encoding UTF8

New-Website -Name $siteName -PhysicalPath $iisRoot -Port 80
Start-Website -Name $siteName

Write-Host "IIS website created and started" -ForegroundColor Green

# Step 7: Configure Windows Firewall
Write-Host ""
Write-Host "Step 7: Configuring Windows Firewall..." -ForegroundColor Green
try {
    New-NetFirewallRule -DisplayName "Drop List - HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -ErrorAction SilentlyContinue
    Write-Host "Firewall rule added for HTTP (port 80)" -ForegroundColor Gray
} catch {
    Write-Host "Firewall rule may already exist or requires manual configuration" -ForegroundColor Yellow
}

# Get server IP
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
Get-Service -Name $serviceName | Format-Table -AutoSize
Write-Host ""

$ipAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" } | Select-Object -ExpandProperty IPAddress
Write-Host "Your application is now running 24/7!" -ForegroundColor Green
Write-Host ""
Write-Host "Access it at:" -ForegroundColor Cyan
foreach ($ip in $ipAddresses) {
    Write-Host "  http://$ip" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  Get-Service DropListApp                    # Check service status" -ForegroundColor Gray
Write-Host "  Restart-Service DropListApp                # Restart service" -ForegroundColor Gray
Write-Host "  Get-Content C:\inetpub\drop-list\service.log -Tail 50  # View logs" -ForegroundColor Gray
Write-Host ""
Write-Host "Log files:" -ForegroundColor Cyan
Write-Host "  Application: C:\inetpub\drop-list\app.log" -ForegroundColor Gray
Write-Host "  Service: C:\inetpub\drop-list\service.log" -ForegroundColor Gray
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
pause
