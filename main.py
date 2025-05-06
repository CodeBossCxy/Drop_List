from fastapi import FastAPI, HTTPException, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import requests
import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
import base64

app = FastAPI()
templates = Jinja2Templates(directory="templates")


app.mount("/static", StaticFiles(directory="static", html=True), name="static")


# --- Config ---
ERP_API_BASE = "https://Vintech-CZ.on.plex.com/api/datasources/"

username = "VintechCZWS@plex.com"
password = "09c11ed-40b3-4"

credentials = f"{username}:{password}"
bytes = credentials.encode('utf-8')
encoded_credentials = base64.b64encode(bytes).decode('utf-8')

authorization_header = f"Basic {encoded_credentials}"
print(authorization_header)


headers = {
  'Authorization': authorization_header,
  'Content-Type': 'application/json'
}

now = datetime.today()


# --- Mock In-Memory Store (can be replaced with DB) ---


# --- Pydantic Models ---
class PartRequest(BaseModel):
    part_no: str

class SerialNoRequest(BaseModel):
    part_no: str
    serial_no: str

# --- ERP Client ---
async def get_containers_by_part_no(part_no: str) -> List[str]:
    containers_by_part_no_id = 8566
    url = f"{ERP_API_BASE}{containers_by_part_no_id}/execute"
    payload = json.dumps({
        "inputs": {
            "Part_No": part_no
        }
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    # print("[get_containers_by_part_no] response:", response.json())
    columns = response.json().get("tables")[0].get("columns", [])
    rows = response.json().get("tables")[0].get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    df = df.sort_values(by="Add_Date")
    print("[get_containers_by_part_no] df:", df['Add_Date'])
    return df.to_dict(orient="records")

# --- API Routes ---

active_connections = []
@app.post("/test")
def test():
    return {"message": "Success"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/part/{part_no}", response_class=JSONResponse)
async def get_containers(request: Request, part_no: str):
    print("part_no", part_no)
    containers = await get_containers_by_part_no(part_no)
    return JSONResponse(content={"dataframe": containers})

@app.post("/part/{part_no}/{serial_no}", response_class=JSONResponse)
async def request_serial_no(request: Request, part_no: str, serial_no: str):
    print("part_no", part_no)
    print("serial_no", serial_no)
    return JSONResponse(content={"message": "Success"})


@app.get("/requests")
async def get_requests(request: Request):
    return templates.TemplateResponse("driver.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Send to all other users (broadcast style)
            for conn in active_connections:
                if conn != websocket:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
