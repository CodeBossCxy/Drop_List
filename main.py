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
import pyodbc
from dotenv import load_dotenv
from decimal import Decimal
from fastapi.encoders import jsonable_encoder
import numpy as np
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

load_dotenv()

# Get connection parameters from environment variables
server = os.getenv('AZURE_SQL_SERVER')
database = os.getenv('AZURE_SQL_DATABASE')
username = os.getenv('AZURE_SQL_USERNAME')
password = os.getenv('AZURE_SQL_PASSWORD')

print("server", server)
print("database", database)
print("username", username)
print("password", password)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Scheduler lifecycle management
@app.on_event("startup")
async def startup_event():
    """Start the background scheduler when the application starts"""
    logger.info("🚀 Starting automated cleanup scheduler...")
    
    # Add the cleanup job to run every 5 minutes
    scheduler.add_job(
        func=automated_container_cleanup,
        trigger=IntervalTrigger(minutes=5),  # Every 5 minutes
        id='container_cleanup',
        name='Automated Container Cleanup',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started successfully")
    
    # Run initial cleanup after 2 minutes (to allow app to fully start)
    scheduler.add_job(
        func=automated_container_cleanup,
        trigger='date',
        run_date=datetime.now() + timedelta(minutes=2),
        id='initial_cleanup',
        name='Initial Container Cleanup'
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the application shuts down"""
    logger.info("🛑 Shutting down scheduler...")
    scheduler.shutdown()
    logger.info("✅ Scheduler shut down successfully")


# global counter
req_id = 0

# your existing routes...

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)


# Validate required environment variables
required_vars = ['AZURE_SQL_SERVER', 'AZURE_SQL_DATABASE', 'AZURE_SQL_USERNAME', 'AZURE_SQL_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class AzureSQLConnection:
    def __init__(self):
        self.connection_string = f'''
            DRIVER={{ODBC Driver 18 for SQL Server}};
            SERVER=tcp:{server}.database.windows.net,1433;
            DATABASE={database};
            Uid={username};
            Pwd={password};
            Encrypt=yes;
            TrustServerCertificate=no;
            Connection Timeout=30;
        '''
        self.conn = None
    
    def __enter__(self):
        self.conn = pyodbc.connect(self.connection_string)
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

# Usage example with context manager
try:
    with AzureSQLConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
        table_count = cursor.fetchone()[0]
        print(f"Connected successfully! Database has {table_count} tables.")
        
except pyodbc.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"General error: {e}")


# --- Config ---
ERP_API_BASE = "https://Vintech-CZ.on.plex.com/api/datasources/"

plex_username = "VintechCZWS@plex.com"
plex_password = "09c11ed-40b3-4"

credentials = f"{plex_username}:{plex_password}"
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
async def get_container_by_serial_no(serial_no: str) -> List[str]:
    container_by_serial_no_id = 4619
    url = f"{ERP_API_BASE}{container_by_serial_no_id}/execute"
    payload = json.dumps({
        "inputs": {
            "Serial_No": serial_no
        }
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    print("-----response-----", response.json())
    columns = response.json().get("tables")[0].get("columns", [])
    rows = response.json().get("tables")[0].get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    print("-----df-----", df)
    return df.to_dict(orient="records")

async def get_containers_by_part_no(part_no: str) -> List[str]:
    containers_by_part_no_id = 8566
    url = f"{ERP_API_BASE}{containers_by_part_no_id}/execute"
    payload = json.dumps({
        "inputs": {
            "Part_No": part_no
        }
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    columns = response.json().get("tables")[0].get("columns", [])
    rows = response.json().get("tables")[0].get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    df = df.sort_values(by=["Add_Date", "Serial_No"], ascending=[True, True])
    
    # Get existing serial numbers from database
    try:
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT serial_no FROM REQUESTS")
            existing_serials = {row[0] for row in cursor.fetchall()}
            
            # Add isRequested column instead of filtering
            df['isRequested'] = df['Serial_No'].isin(existing_serials)
            
    except Exception as e:
        print(f"Error checking existing containers: {e}")
        df['isRequested'] = False
    
    print("[get_containers_by_part_no] df:", df[['Serial_No', 'Part_No', 'Revision', 'Quantity', 'Location', 'isRequested']])
    
    # Filter out containers from locations starting with "J-B"
    df = df[~df['Location'].str.startswith('J-B', na=False)]
    
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    return df.to_dict(orient="records")

async def get_prod_locations() -> List[str]:
    prod_locations_id = 18120
    url = f"{ERP_API_BASE}{prod_locations_id}/execute"
    payload = json.dumps({
        "inputs": {
            "Location_Type": "Production Storage_IN"
        }
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    # print("[get_prod_locations] response:", response.json())
    columns = response.json().get("tables")[0].get("columns", [])
    rows = response.json().get("tables")[0].get("rows", [])
    df = pd.DataFrame(rows, columns=columns)
    print(df)
    return df['Location'].tolist()

# --- Automated Cleanup Functions ---

async def check_container_current_location(serial_no: str) -> Optional[str]:
    """
    Check the current location of a container by its serial number
    Returns the current location or None if not found
    """
    try:
        logger.info(f"🔍 Checking current location for container: {serial_no}")
        container_data = await get_container_by_serial_no(serial_no)
        
        if container_data and len(container_data) > 0:
            current_location = container_data[0].get('Location')
            logger.info(f"📍 Container {serial_no} current location: {current_location}")
            return current_location
        else:
            logger.warning(f"⚠️ Container {serial_no} not found in ERP system")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error checking location for container {serial_no}: {e}")
        return None

async def automated_container_cleanup():
    """
    Main automated cleanup function that runs every 5 minutes
    Checks if requested containers have moved to production locations and removes them
    """
    try:
        logger.info("🧹 Starting automated container cleanup...")
        
        # Get all production locations
        logger.info("📋 Fetching production locations...")
        prod_locations = await get_prod_locations()
        logger.info(f"✅ Found {len(prod_locations)} production locations: {prod_locations}")
        
        # Get all active requests from database
        logger.info("🗄️ Fetching active requests from database...")
        
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT req_id, serial_no, part_no, location, deliver_to, req_time 
                FROM REQUESTS 
                ORDER BY req_time DESC
            """)
            active_requests = cursor.fetchall()
            
        logger.info(f"📊 Found {len(active_requests)} active requests to check")
        
        containers_to_remove = []
        
        # Check each active request
        for req_id, serial_no, part_no, stored_location, deliver_to, req_time in active_requests:
            logger.info(f"🔍 Checking container: {serial_no} (stored location: {stored_location})")
            
            # Get current location from ERP
            current_location = await check_container_current_location(serial_no)
            
            if current_location:
                # Check if current location is in production locations
                if current_location in prod_locations:
                    logger.info(f"🎯 Container {serial_no} found in production location: {current_location}")
                    containers_to_remove.append({
                        'req_id': req_id,
                        'serial_no': serial_no,
                        'part_no': part_no,
                        'stored_location': stored_location,
                        'current_location': current_location,
                        'deliver_to': deliver_to,
                        'req_time': req_time
                    })
                else:
                    logger.info(f"📍 Container {serial_no} still at non-production location: {current_location}")
            else:
                logger.warning(f"⚠️ Could not determine current location for container: {serial_no}")
            
            # Small delay to avoid overwhelming the ERP API
            await asyncio.sleep(1)
        
        # Remove containers that are now in production locations
        if containers_to_remove:
            logger.info(f"🗑️ Removing {len(containers_to_remove)} containers that moved to production...")
            
            with AzureSQLConnection() as conn:
                cursor = conn.cursor()
                
                for container in containers_to_remove:
                    try:
                        cursor.execute("DELETE FROM REQUESTS WHERE req_id = ?", (container['req_id'],))
                        logger.info(f"✅ Removed container {container['serial_no']} from requests (moved to {container['current_location']})")
                    except Exception as e:
                        logger.error(f"❌ Error removing container {container['serial_no']}: {e}")
                
                conn.commit()
                logger.info(f"✅ Successfully processed {len(containers_to_remove)} container removals")
        else:
            logger.info("✅ No containers need to be removed at this time")
        
        logger.info(f"🏁 Automated cleanup completed successfully. Checked {len(active_requests)} requests, removed {len(containers_to_remove)} containers")
        
    except Exception as e:
        logger.error(f"❌ Error in automated cleanup: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

async def manual_container_cleanup():
    """
    Manual version of the cleanup function for testing/debugging
    Returns detailed results instead of just logging
    """
    try:
        logger.info("🔧 Starting manual container cleanup...")
        
        results = {
            'status': 'success',
            'checked_requests': 0,
            'removed_containers': 0,
            'prod_locations': [],
            'containers_removed': [],
            'errors': []
        }
        
        # Get production locations
        prod_locations = await get_prod_locations()
        results['prod_locations'] = prod_locations
        
        # Get active requests
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT req_id, serial_no, part_no, location, deliver_to, req_time 
                FROM REQUESTS 
                ORDER BY req_time DESC
            """)
            active_requests = cursor.fetchall()
            
        results['checked_requests'] = len(active_requests)
        
        containers_to_remove = []
        
        # Check each request
        for req_id, serial_no, part_no, stored_location, deliver_to, req_time in active_requests:
            try:
                current_location = await check_container_current_location(serial_no)
                
                if current_location and current_location in prod_locations:
                    container_info = {
                        'req_id': req_id,
                        'serial_no': serial_no,
                        'part_no': part_no,
                        'stored_location': stored_location,
                        'current_location': current_location,
                        'deliver_to': deliver_to,
                        'req_time': req_time.isoformat() if isinstance(req_time, datetime) else str(req_time)
                    }
                    containers_to_remove.append(container_info)
                    results['containers_removed'].append(container_info)
                    
            except Exception as e:
                error_msg = f"Error checking container {serial_no}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            await asyncio.sleep(0.5)  # Shorter delay for manual testing
        
        # Remove containers
        if containers_to_remove:
            with AzureSQLConnection() as conn:
                cursor = conn.cursor()
                
                for container in containers_to_remove:
                    try:
                        cursor.execute("DELETE FROM REQUESTS WHERE req_id = ?", (container['req_id'],))
                    except Exception as e:
                        error_msg = f"Error removing container {container['serial_no']}: {str(e)}"
                        results['errors'].append(error_msg)
                
                conn.commit()
        
        results['removed_containers'] = len(containers_to_remove)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in manual cleanup: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'checked_requests': 0,
            'removed_containers': 0
        }

# --- API Routes ---

active_connections = []
@app.post("/test")
def test():
    return {"message": "Success"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # # Make your API call here
    # try:
    #     # Example API call - replace with your actual API endpoint
    #     api_response = requests.get("YOUR_API_ENDPOINT", headers=headers)
    #     api_data = api_response.json()
    # except Exception as e:
    #     print(f"API call failed: {e}")
    #     api_data = None
    locations = await get_prod_locations() + ['J-B3']
    # Pass both the request and API data to the template
    print("locations", locations)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "prod_locations": locations
    })


@app.post("/part/{part_no}", response_class=JSONResponse)
async def get_containers(request: Request, part_no: str):
    print("part_no", part_no)
    containers = await get_containers_by_part_no(part_no)
    # return JSONResponse(content={"dataframe": containers.to_dict(orient="records")})
    return JSONResponse(content={"dataframe": jsonable_encoder(containers)})

@app.post("/part/{part_no}/{serial_no}", response_class=JSONResponse)
async def request_serial_no(request: Request, part_no: str, serial_no: str):
    global req_id
    print("part_no", part_no)
    print("serial_no", serial_no)
    data = await request.json()
    print("req_id", req_id)
    print("data", data)

    try:
        with AzureSQLConnection() as conn:
            
            print(req_id, part_no, serial_no, data['location'], data['workcenter'], data['req_time'])
            cursor = conn.cursor()
            cursor.execute("INSERT INTO REQUESTS (req_id, serial_no, part_no, revision, quantity, location, deliver_to, req_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (req_id, serial_no, part_no, data['revision'], data['quantity'], data['location'], data['workcenter'], data['req_time']))
            conn.commit()

            if cursor.rowcount == 1:
                print("Request inserted successfully")
                req_id += 1
            else:
                print("Request insertion failed")

    except Exception as e:
        print(f"Error inserting request: {e}")
        return JSONResponse(content={"message": "Error"})

    return JSONResponse(content={"message": "Success"})

@app.post("/{serial_no}", response_class=JSONResponse)
async def request_serial_no(request: Request, serial_no: str):
    global req_id
    print("serial_no", serial_no)
    container = await get_container_by_serial_no(serial_no)
    print("-----container-----", container)
    return JSONResponse(content={"dataframe": jsonable_encoder(container)})


@app.get("/requests", response_class=HTMLResponse)
async def get_requests(request: Request):
    # Make your API call here
    try:
        # Example API call - replace with your actual API endpoint
        api_response = requests.get("YOUR_API_ENDPOINT", headers=headers)
        api_data = api_response.json()
    except Exception as e:
        print(f"API call failed: {e}")
        api_data = None

    # Pass both the request and API data to the template
    return templates.TemplateResponse("driver.html", {
        "request": request,
        "api_data": api_data
    })


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

@app.get("/barcode/{location}", response_class=JSONResponse)
async def get_barcode(location: str):
    try:
        # Replace this with your actual API call to get the barcode
        # Example:
        # barcode_api_url = f"YOUR_BARCODE_API_URL/{location}"
        # response = requests.get(barcode_api_url, headers=headers)
        # barcode = response.json().get("barcode")
        
        # For now, returning a mock barcode
        barcode = f"BC-{location}"
        
        return JSONResponse(content={"barcode": barcode})
    except Exception as e:
        print(f"Error fetching barcode: {e}")
        return JSONResponse(content={"barcode": "N/A"})

@app.get("/api/requests", response_class=JSONResponse)
async def get_all_requests():
    try:
        print("Attempting to connect to database...")
        with AzureSQLConnection() as conn:
            print("Connected to database successfully")
            cursor = conn.cursor()
            print("Executing SQL query...")
            cursor.execute("""
                SELECT *
                FROM REQUESTS 
                ORDER BY req_time DESC
            """)
            print("Query executed successfully")
            columns = [column[0] for column in cursor.description]
            print(f"Columns found: {columns}")
            requests = []
            rows = cursor.fetchall()
            print(f"Number of rows fetched: {len(rows)}")
            
            for row in rows:
                # Convert row to dict and handle datetime serialization
                request_dict = {}
                for i, value in enumerate(row):
                    if isinstance(value, datetime):
                        request_dict[columns[i]] = value.isoformat()
                    elif isinstance(value, Decimal):
                        request_dict[columns[i]] = float(value)
                    else:
                        request_dict[columns[i]] = value
                requests.append(request_dict)
            
            print("Successfully processed all rows")
            return JSONResponse(content=requests)
    except Exception as e:
        print(f"Error fetching requests: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/requests/{serial_no}", response_class=JSONResponse)
async def delete_request(serial_no: str):
    try:
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM REQUESTS WHERE serial_no = ?", (serial_no,))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Request not found")
                
            return JSONResponse(content={"message": "Request deleted successfully"})
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error deleting request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Automated Cleanup API Endpoints ---

@app.post("/api/cleanup/manual", response_class=JSONResponse)
async def trigger_manual_cleanup():
    """
    Manual endpoint to trigger container cleanup for testing/debugging
    Returns detailed results about what was cleaned up
    """
    try:
        logger.info("🔧 Manual cleanup triggered via API")
        results = await manual_container_cleanup()
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Error in manual cleanup API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cleanup/status", response_class=JSONResponse)
async def get_cleanup_status():
    """
    Get status information about the automated cleanup system
    """
    try:
        # Get scheduler info
        jobs = scheduler.get_jobs()
        cleanup_job = next((job for job in jobs if job.id == 'container_cleanup'), None)
        
        status_info = {
            'scheduler_running': scheduler.running,
            'cleanup_job_active': cleanup_job is not None,
            'next_run_time': None,
            'jobs_count': len(jobs),
            'last_cleanup_time': None  # You could store this in a file or database if needed
        }
        
        if cleanup_job:
            status_info['next_run_time'] = cleanup_job.next_run_time.isoformat() if cleanup_job.next_run_time else None
        
        # Get current database statistics
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM REQUESTS")
            active_requests_count = cursor.fetchone()[0]
            
        status_info['active_requests_count'] = active_requests_count
        
        return JSONResponse(content=status_info)
        
    except Exception as e:
        logger.error(f"Error getting cleanup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cleanup/logs", response_class=JSONResponse)
async def get_cleanup_logs():
    """
    Get recent cleanup logs (if you want to implement log storage)
    For now, returns basic information
    """
    try:
        # This could be enhanced to return actual log entries
        # For now, return basic system information
        
        prod_locations = await get_prod_locations()
        
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total_requests, 
                       MIN(req_time) as oldest_request,
                       MAX(req_time) as newest_request
                FROM REQUESTS
            """)
            stats = cursor.fetchone()
        
        return JSONResponse(content={
            'production_locations': prod_locations,
            'total_active_requests': stats[0] if stats else 0,
            'oldest_request': stats[1].isoformat() if stats and stats[1] else None,
            'newest_request': stats[2].isoformat() if stats and stats[2] else None,
            'system_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cleanup logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
