# Drop List Web App - Company Server Deployment Guide

This guide will help you deploy the Drop List application on your company server so that employees connected to the company WiFi can access it.

## Prerequisites

- A Linux server (Ubuntu/Debian recommended) or Windows Server
- Root/Administrator access to the server
- Python 3.10 or higher
- Network access from the server to your Azure SQL database
- Server should be accessible on the company network

---

## Step 1: Prepare the Server

### For Linux (Ubuntu/Debian):

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Python 3.10+ and pip
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies for ODBC (required for SQL Server connection)
sudo apt install unixodbc unixodbc-dev -y

# Install Microsoft ODBC Driver for SQL Server
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install msodbcsql18 -y
```

### For Windows Server:

1. Install Python 3.10+ from https://www.python.org/downloads/
2. Install Microsoft ODBC Driver 18 for SQL Server from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
3. Open PowerShell as Administrator for the following steps

---

## Step 2: Transfer Application Files to Server

### Option A: Using Git (Recommended)

```bash
# Install git if not already installed
sudo apt install git -y  # Linux
# or download Git for Windows

# Clone/Pull the repository to the server
cd /opt  # or C:\inetpub\ for Windows
git clone <your-repository-url> drop-list
cd drop-list
```

### Option B: Manual Transfer

Use SCP, SFTP, or file sharing to copy the entire project folder to the server:
- Linux: `/opt/drop-list/`
- Windows: `C:\inetpub\drop-list\`

---

## Step 3: Set Up Python Environment

```bash
# Navigate to the application directory
cd /opt/drop-list  # or cd C:\inetpub\drop-list for Windows

# Create a virtual environment
python3 -m venv venv  # Linux
# or
python -m venv venv  # Windows

# Activate the virtual environment
source venv/bin/activate  # Linux
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4: Configure Environment Variables

The `.env` file contains your database credentials. **IMPORTANT: Keep this file secure!**

Your current `.env` file is already configured:
```
AZURE_SQL_SERVER = vintechpicklist
AZURE_SQL_DATABASE = VintechPickList
AZURE_SQL_USERNAME  = picklistdb
AZURE_SQL_PASSWORD = 1528814Cxy@Fighting
```

Verify the file exists and has correct permissions:

```bash
# Linux - restrict permissions
chmod 600 .env

# Windows - restrict access via File Properties > Security
```

---

## Step 5: Test the Application

Before deploying, test that the application runs:

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux
# or
.\venv\Scripts\activate  # Windows

# Run the application manually
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open a browser and test:
- From the server: `http://localhost:8000`
- From another computer on the network: `http://<server-ip>:8000`

To find your server IP:
```bash
# Linux
ip addr show | grep inet

# Windows
ipconfig
```

**If it works, press Ctrl+C to stop the test server and proceed to the next step.**

---

## Step 6: Set Up Application as a Service (Linux)

To keep the application running permanently, create a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/drop-list.service
```

Paste the following content (adjust paths if needed):

```ini
[Unit]
Description=Drop List FastAPI Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/drop-list
Environment="PATH=/opt/drop-list/venv/bin"
ExecStart=/opt/drop-list/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable drop-list

# Start the service
sudo systemctl start drop-list

# Check status
sudo systemctl status drop-list
```

Useful commands:
```bash
# View logs
sudo journalctl -u drop-list -f

# Restart service
sudo systemctl restart drop-list

# Stop service
sudo systemctl stop drop-list
```

---

## Step 6: Set Up Application as a Service (Windows)

### Option A: Use NSSM (Recommended)

1. Download NSSM from https://nssm.cc/download
2. Extract and open PowerShell as Administrator:

```powershell
# Navigate to NSSM directory
cd C:\path\to\nssm\win64

# Install the service
.\nssm.exe install DropListApp "C:\inetpub\drop-list\venv\Scripts\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"

# Set working directory
.\nssm.exe set DropListApp AppDirectory "C:\inetpub\drop-list"

# Set to start automatically
.\nssm.exe set DropListApp Start SERVICE_AUTO_START

# Start the service
.\nssm.exe start DropListApp
```

### Option B: Use Task Scheduler

Create a scheduled task that runs at system startup with the command:
```
C:\inetpub\drop-list\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Step 7: Configure Firewall

### Linux (UFW):

```bash
# Allow port 8000
sudo ufw allow 8000/tcp

# Or allow from specific subnet (e.g., company network 192.168.1.0/24)
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

### Windows:

```powershell
# Open PowerShell as Administrator
New-NetFirewallRule -DisplayName "Drop List App" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## Step 8: Access the Application

Employees can now access the application using:

**http://\<server-ip\>:8000**

For example:
- `http://192.168.1.100:8000`
- `http://company-server.local:8000`

To use a friendly hostname instead of IP:
1. Ask your IT department to create a DNS entry (e.g., `droplist.company.local`)
2. Or add entries to each computer's hosts file

---

## Step 9 (Optional): Set Up Reverse Proxy with Nginx

For production use, it's recommended to use Nginx as a reverse proxy:

### Install Nginx:

```bash
sudo apt install nginx -y
```

### Configure Nginx:

```bash
sudo nano /etc/nginx/sites-available/drop-list
```

Paste this configuration:

```nginx
server {
    listen 80;
    server_name droplist.company.local;  # or use server IP

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/drop-list /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Allow HTTP through firewall
sudo ufw allow 'Nginx HTTP'
```

Now users can access via: **http://droplist.company.local** or **http://\<server-ip\>**

---

## Troubleshooting

### Application won't start:

```bash
# Check logs
sudo journalctl -u drop-list -n 50  # Linux

# Check if port is in use
sudo netstat -tulpn | grep 8000  # Linux
netstat -ano | findstr :8000  # Windows
```

### Cannot connect from other computers:

1. Verify firewall allows connections
2. Check server IP is correct
3. Ensure application is bound to `0.0.0.0` not `127.0.0.1`
4. Test with: `curl http://<server-ip>:8000` from another machine

### Database connection issues:

1. Verify Azure SQL server firewall allows your server's IP
2. Test connection: `telnet vintechpicklist.database.windows.net 1433`
3. Check `.env` file credentials are correct

### Updates and Maintenance:

```bash
# Pull latest changes
cd /opt/drop-list
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies if needed
pip install -r requirements.txt

# Restart service
sudo systemctl restart drop-list
```

---

## Security Recommendations

1. **Restrict Access**: Configure firewall to only allow company network subnet
2. **Use HTTPS**: Set up SSL certificate with Let's Encrypt or company CA
3. **Secure .env**: Ensure `.env` file has restricted permissions (chmod 600)
4. **Regular Updates**: Keep Python, dependencies, and OS packages updated
5. **Backup Database**: Set up regular backups of Azure SQL database
6. **Monitor Logs**: Regularly check application logs for errors or suspicious activity

---

## Quick Reference

### Service Management (Linux):
```bash
sudo systemctl start drop-list      # Start
sudo systemctl stop drop-list       # Stop
sudo systemctl restart drop-list    # Restart
sudo systemctl status drop-list     # Check status
sudo journalctl -u drop-list -f     # View logs
```

### Service Management (Windows with NSSM):
```powershell
nssm start DropListApp      # Start
nssm stop DropListApp       # Stop
nssm restart DropListApp    # Restart
nssm status DropListApp     # Check status
```

### Application URL:
- Direct: `http://<server-ip>:8000`
- With Nginx: `http://<server-ip>` or `http://droplist.company.local`

---

## Support

For issues or questions:
1. Check application logs: `sudo journalctl -u drop-list -n 100`
2. Review this deployment guide
3. Contact your IT department for server/network issues
