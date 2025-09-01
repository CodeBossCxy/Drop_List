#!/bin/bash
# Azure Web App startup script

# Install requirements if needed
pip install -r requirements.txt

# Start the application
gunicorn --bind 0.0.0.0:$PORT --worker-class uvicorn.workers.UvicornWorker --workers 1 main:app