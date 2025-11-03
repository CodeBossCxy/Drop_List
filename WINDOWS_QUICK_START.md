# Windows Server - Super Quick Start Guide

The **FASTEST** way to get your Drop List app running 24/7 on Windows Server with clean URLs.

---

## Prerequisites (Install These First)

1. **Python 3.10+** - https://python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **ODBC Driver 18 for SQL Server** - https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
   - ✅ Just click through the installer

---

## Super Fast Setup (3 Steps!)

### Step 1: Copy Files to Server

Copy your entire "Drop List" folder to the Windows server. Use any method:
- Remote Desktop (copy/paste)
- Network share
- USB drive

### Step 2: Run the Setup Script

1. **Open PowerShell as Administrator**
   - Press `Windows key`
   - Type "PowerShell"
   - Right-click "Windows PowerShell"
   - Click "Run as Administrator"

2. **Navigate to your folder:**
   ```powershell
   cd "C:\path\to\Drop List"
   ```

3. **Allow scripts (one-time only):**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Run setup:**
   ```powershell
   .\setup-windows.ps1
   ```

   The script will automatically:
   - ✅ Check Python and ODBC
   - ✅ Install all dependencies
   - ✅ Create Windows Service (24/7 auto-start)
   - ✅ Setup IIS reverse proxy (clean URLs)
   - ✅ Configure firewall
   - ✅ Start everything

### Step 3: Access Your App

From any computer on your company network, open browser and go to:

**http://YOUR-SERVER-IP**

To find your server IP, the setup script shows it at the end, or run:
```powershell
ipconfig
```

Look for "IPv4 Address" (usually something like 192.168.1.100)

---

## Managing Your App

### Easy Way - Use the Batch File:

Double-click **`manage-service.bat`** (Run as Administrator) for a menu to:
- Check status
- Start/Stop/Restart
- View logs

### Command Line Way:

```powershell
# Check status
Get-Service DropListApp

# Restart service
Restart-Service DropListApp

# View logs
Get-Content C:\inetpub\drop-list\service.log -Tail 50
```

---

## Common Issues & Fixes

### "Can't access from other computers"

1. Check firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "Drop List - HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
   ```

2. Make sure service is running:
   ```powershell
   Get-Service DropListApp
   ```

3. Check IIS is running:
   ```powershell
   Get-Website
   ```

### "Service won't start"

Check error logs:
```powershell
Get-Content C:\inetpub\drop-list\service_error.log -Tail 20
```

Common fix - Restart service:
```powershell
Restart-Service DropListApp
```

### "IIS shows error page"

Make sure Python app is running first:
```powershell
Get-Service DropListApp
```

If stopped, start it:
```powershell
Start-Service DropListApp
```

Then restart IIS:
```powershell
iisreset
```

---

## Updating the App

When you have new code:

```powershell
# Stop service
Stop-Service DropListApp

# Copy new files to C:\inetpub\drop-list

# Start service
Start-Service DropListApp
```

---

## Architecture

```
Employee Browser
    ↓
http://server-ip (port 80)
    ↓
IIS (reverse proxy)
    ↓
Windows Service (DropListApp)
    ↓
Your Python App
    ↓
Azure SQL Database
```

**Benefits:**
- ✅ Runs 24/7, auto-starts on boot
- ✅ Clean URLs (no :8000)
- ✅ Professional setup with IIS
- ✅ Automatic restart if app crashes

---

## Files Created

- **`setup-windows.ps1`** - Automated setup script (run once)
- **`manage-service.bat`** - Easy service management (run anytime)
- **`WINDOWS_SETUP.md`** - Detailed manual setup guide
- **`WINDOWS_QUICK_START.md`** - This file!

---

## Need Help?

1. Check logs: `C:\inetpub\drop-list\service.log`
2. Review **WINDOWS_SETUP.md** for detailed troubleshooting
3. Use **manage-service.bat** to check status and view logs

---

## Security Tips

- ✅ Keep `.env` file secure (contains database password)
- ✅ Regularly update Windows and Python packages
- ✅ Consider HTTPS for production use
- ✅ Backup your Azure SQL database regularly

---

That's it! Your app is now running 24/7 with professional IIS hosting and clean URLs! 🚀
