#!/bin/bash

# Drop List Web App - Server Setup Script
# This script sets up the application to run 24/7 with Nginx

set -e  # Exit on any error

echo "=========================================="
echo "Drop List Application Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="/opt/drop-list"

echo "Step 1: Installing system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv nginx unixodbc unixodbc-dev

# Install Microsoft ODBC Driver for SQL Server if not already installed
if ! dpkg -l | grep -q msodbcsql18; then
    echo "Installing Microsoft ODBC Driver 18 for SQL Server..."
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
    curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list
    apt update
    ACCEPT_EULA=Y apt install -y msodbcsql18
fi

echo ""
echo "Step 2: Setting up application directory..."
# Copy application files to /opt/drop-list if not already there
if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
    mkdir -p /opt
    if [ -d "$APP_DIR" ]; then
        echo "Backing up existing installation..."
        mv "$APP_DIR" "$APP_DIR.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    cp -r "$SCRIPT_DIR" "$APP_DIR"
    cd "$APP_DIR"
else
    cd "$APP_DIR"
fi

echo ""
echo "Step 3: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 4: Setting up systemd service..."
cp drop-list.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable drop-list
systemctl restart drop-list

echo ""
echo "Step 5: Configuring Nginx..."
cp nginx-drop-list.conf /etc/nginx/sites-available/drop-list
ln -sf /etc/nginx/sites-available/drop-list /etc/nginx/sites-enabled/drop-list

# Remove default nginx site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

# Test nginx configuration
nginx -t

# Restart nginx
systemctl restart nginx

echo ""
echo "Step 6: Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 'Nginx HTTP'
    ufw allow 'Nginx HTTPS'
    echo "Firewall rules added"
else
    echo "UFW not found, skipping firewall configuration"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service Status:"
systemctl status drop-list --no-pager | head -n 10
echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager | head -n 5
echo ""
echo "=========================================="
echo "Your application is now running 24/7!"
echo ""
echo "Access it at:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status drop-list    # Check app status"
echo "  sudo systemctl restart drop-list   # Restart app"
echo "  sudo journalctl -u drop-list -f    # View app logs"
echo "  sudo systemctl restart nginx       # Restart nginx"
echo "=========================================="
