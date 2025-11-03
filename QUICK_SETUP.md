# Quick Setup Guide - 24/7 Running with Clean URLs

This guide will set up your Drop List application to:
- Run 24/7 automatically (even after server reboots)
- Use clean URLs without port numbers (e.g., `http://192.168.1.100` instead of `http://192.168.1.100:8000`)

---

## Option 1: Automated Setup (Recommended)

Transfer all files to your Linux server, then run:

```bash
# Copy files to server (from your local machine)
scp -r /path/to/drop-list your-user@server-ip:/tmp/

# On the server, run the setup script
ssh your-user@server-ip
cd /tmp/drop-list
sudo ./setup-server.sh
```

That's it! The script will handle everything automatically.

---

## Option 2: Manual Setup

If you prefer to set up manually or the script doesn't work:

### 1. Transfer files to server

```bash
# Copy your project to the server
sudo mkdir -p /opt/drop-list
sudo cp -r ./* /opt/drop-list/
cd /opt/drop-list
```

### 2. Install dependencies

```bash
# Install system packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx unixodbc unixodbc-dev

# Install Microsoft ODBC Driver
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set up the systemd service (for 24/7 running)

```bash
# Copy service file
sudo cp drop-list.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable drop-list
sudo systemctl start drop-list

# Check if it's running
sudo systemctl status drop-list
```

### 4. Set up Nginx (for clean URLs)

```bash
# Copy nginx configuration
sudo cp nginx-drop-list.conf /etc/nginx/sites-available/drop-list

# Enable the site
sudo ln -s /etc/nginx/sites-available/drop-list /etc/nginx/sites-enabled/drop-list

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 5. Configure firewall

```bash
# Allow HTTP traffic
sudo ufw allow 'Nginx HTTP'
```

---

## Verify Everything is Working

```bash
# Check application service
sudo systemctl status drop-list

# Check nginx
sudo systemctl status nginx

# View application logs
sudo journalctl -u drop-list -f

# Test from server
curl http://localhost

# Get server IP
ip addr show | grep inet
```

Then from another computer on the company network, open a browser and go to:
**http://YOUR-SERVER-IP**

Example: `http://192.168.1.100`

---

## Configure Custom Hostname (Optional)

Instead of using the IP address, you can set up a friendly name:

### Option A: Ask IT to create DNS entry
Request your IT department to create a DNS record like:
- `droplist.company.local` → Your server IP

### Option B: Edit Nginx config for specific hostname

Edit the nginx config:
```bash
sudo nano /etc/nginx/sites-available/drop-list
```

Change this line:
```nginx
server_name _;
```

To:
```nginx
server_name droplist.company.local;
```

Then restart nginx:
```bash
sudo systemctl restart nginx
```

---

## Managing the Application

### Service Commands:

```bash
# Start application
sudo systemctl start drop-list

# Stop application
sudo systemctl stop drop-list

# Restart application
sudo systemctl restart drop-list

# Check status
sudo systemctl status drop-list

# View real-time logs
sudo journalctl -u drop-list -f

# View last 100 log lines
sudo journalctl -u drop-list -n 100
```

### When you update the code:

```bash
# Pull new changes (if using git)
cd /opt/drop-list
git pull

# Or copy new files manually
sudo cp /path/to/new/files/* /opt/drop-list/

# Restart the service
sudo systemctl restart drop-list
```

---

## Troubleshooting

### Application won't start:

```bash
# Check logs for errors
sudo journalctl -u drop-list -n 50

# Check if port 8000 is already in use
sudo netstat -tulpn | grep 8000

# Verify .env file exists
ls -la /opt/drop-list/.env
```

### Can't access from other computers:

```bash
# Check nginx is running
sudo systemctl status nginx

# Check firewall
sudo ufw status

# Verify nginx is listening on port 80
sudo netstat -tulpn | grep :80

# Test locally first
curl http://localhost
```

### Database connection errors:

```bash
# Check .env file has correct credentials
cat /opt/drop-list/.env

# Test Azure SQL connectivity
telnet vintechpicklist.database.windows.net 1433

# Make sure Azure SQL firewall allows your server's public IP
```

---

## What Each File Does

- **drop-list.service** - Makes the app run 24/7 and auto-start on boot
- **nginx-drop-list.conf** - Nginx configuration for clean URLs (removes :8000)
- **setup-server.sh** - Automated setup script that does everything for you
- **.env** - Database credentials (keep this secure!)
- **main.py** - Main application code
- **requirements.txt** - Python dependencies

---

## Architecture Overview

```
User's Browser
    ↓
http://server-ip (port 80)
    ↓
Nginx (reverse proxy)
    ↓
http://127.0.0.1:8000 (internal)
    ↓
Your FastAPI App (Gunicorn + Uvicorn)
    ↓
Azure SQL Database
```

Benefits:
- Nginx handles SSL, compression, static files efficiently
- Application runs on internal port 8000 (not exposed)
- Users access via clean URL on port 80
- Systemd keeps app running 24/7 and restarts if it crashes

---

## Next Steps

1. Run the setup
2. Test accessing from multiple devices on company WiFi
3. Consider adding HTTPS with SSL certificate
4. Set up regular backups
5. Monitor logs regularly

For detailed documentation, see `DEPLOYMENT_GUIDE.md`
