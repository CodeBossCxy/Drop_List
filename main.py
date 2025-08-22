from fastapi import FastAPI, HTTPException, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import requests
import os
import json
from datetime import datetime, timedelta, timezone
import pytz
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

# Define Czech timezone
CZECH_TIMEZONE = pytz.timezone('Europe/Prague')

def convert_to_czech_timezone(dt):
    """Convert datetime to Czech timezone and return as ISO string"""
    if dt is None:
        return None
    
    # If datetime is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    # Convert to Czech timezone
    czech_time = dt.astimezone(CZECH_TIMEZONE)
    return czech_time.isoformat()

def get_shift_from_czech_datetime(dt):
    """
    Determine which shift a datetime falls into based on Czech timezone
    Shifts:
    - Morning: 6:00-14:00 (6 AM to 2 PM)
    - Evening: 14:00-22:00 (2 PM to 10 PM)
    - Night: 22:00-6:00 (10 PM to 6 AM, crosses midnight)
    
    Args:
        dt: datetime object (will be converted to Czech timezone if needed)
    
    Returns:
        str: 'Morning', 'Evening', or 'Night'
    """
    if dt is None:
        return 'Unknown'
    
    # Convert to Czech timezone
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    czech_time = dt.astimezone(CZECH_TIMEZONE)
    
    hour = czech_time.hour
    
    if 6 <= hour < 14:
        return 'Morning'
    elif 14 <= hour < 22:
        return 'Evening'
    else:  # hour >= 22 or hour < 6
        return 'Night'

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
    
    # Add the history cleanup job to run daily at 2 AM
    scheduler.add_job(
        func=automated_history_cleanup,
        trigger='cron',
        hour=2,
        minute=0,
        id='history_cleanup',
        name='Automated History Cleanup (30+ days)',
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started successfully (container cleanup: 5min, history cleanup: daily)")
    
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

# --- Database Setup Functions ---

def create_history_table():
    """Create REQUESTS_HISTORY table if it doesn't exist"""
    create_table_sql = """
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'REQUESTS_HISTORY')
    BEGIN
        CREATE TABLE REQUESTS_HISTORY (
            history_id INT IDENTITY(1,1) PRIMARY KEY,
            req_id INT,
            serial_no NVARCHAR(255),
            part_no NVARCHAR(255),
            revision NVARCHAR(50),
            quantity DECIMAL(10,2),
            location NVARCHAR(255),
            deliver_to NVARCHAR(255),
            req_time DATETIME,
            fulfilled_time DATETIME,
            fulfillment_duration_minutes INT,
            fulfillment_type NVARCHAR(50),
            current_location NVARCHAR(255)
        );
        
        -- Create indexes for better performance
        CREATE INDEX IX_REQUESTS_HISTORY_serial_no ON REQUESTS_HISTORY(serial_no);
        CREATE INDEX IX_REQUESTS_HISTORY_part_no ON REQUESTS_HISTORY(part_no);
        CREATE INDEX IX_REQUESTS_HISTORY_req_time ON REQUESTS_HISTORY(req_time);
        CREATE INDEX IX_REQUESTS_HISTORY_fulfilled_time ON REQUESTS_HISTORY(fulfilled_time);
        
        PRINT 'REQUESTS_HISTORY table and indexes created successfully.';
    END
    ELSE
    BEGIN
        PRINT 'REQUESTS_HISTORY table already exists.';
    END
    """
    
    try:
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info("✅ REQUESTS_HISTORY table setup completed")
    except Exception as e:
        logger.error(f"❌ Error creating REQUESTS_HISTORY table: {e}")

# Usage example with context manager and setup
try:
    with AzureSQLConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
        table_count = cursor.fetchone()[0]
        print(f"Connected successfully! Database has {table_count} tables.")
        
    # Create history table on startup
    create_history_table()
        
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

# --- History Logging Functions ---

def log_request_to_history(req_id: int, serial_no: str, part_no: str, revision: str, quantity: float, 
                          location: str, deliver_to: str, req_time: datetime, 
                          current_location: str, fulfillment_type: str = 'auto_cleanup'):
    """
    Log a fulfilled request to the REQUESTS_HISTORY table
    """
    try:
        # Store fulfilled time in UTC (database should store in UTC)
        fulfilled_time = datetime.utcnow()
        
        # Ensure req_time is in UTC for calculation
        if req_time.tzinfo is None:
            # If req_time is naive, assume it's already UTC (which it should be from our storage)
            req_time_utc = req_time
        else:
            # Convert to UTC for calculation
            req_time_utc = req_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
        # Calculate fulfillment duration in minutes (should be positive)
        duration_minutes = int((fulfilled_time - req_time_utc).total_seconds() / 60)
        
        # Log timing info for debugging
        logger.info(f"History logging: req_time={req_time_utc}, fulfilled_time={fulfilled_time}, duration={duration_minutes}min")
        
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO REQUESTS_HISTORY 
                (req_id, serial_no, part_no, revision, quantity, location, deliver_to, 
                 req_time, fulfilled_time, fulfillment_duration_minutes, fulfillment_type, current_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (req_id, serial_no, part_no, revision, quantity, location, deliver_to,
                  req_time, fulfilled_time, duration_minutes, fulfillment_type, current_location))
            conn.commit()
            
        logger.info(f"📝 Logged request {serial_no} to history (fulfilled in {duration_minutes} minutes)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging request {serial_no} to history: {e}")
        return False

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
                SELECT req_id, serial_no, part_no, revision, quantity, location, deliver_to, req_time 
                FROM REQUESTS 
                ORDER BY req_time DESC
            """)
            active_requests = cursor.fetchall()
            
        logger.info(f"📊 Found {len(active_requests)} active requests to check")
        
        containers_to_remove = []
        
        # Check each active request
        for req_id, serial_no, part_no, revision, quantity, stored_location, deliver_to, req_time in active_requests:
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
                        'revision': revision,
                        'quantity': quantity,
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
                        # Log to history before deleting
                        history_logged = log_request_to_history(
                            req_id=container['req_id'],
                            serial_no=container['serial_no'],
                            part_no=container['part_no'],
                            revision=container['revision'] or '',
                            quantity=float(container['quantity']) if container['quantity'] else 0.0,
                            location=container['stored_location'],
                            deliver_to=container['deliver_to'],
                            req_time=container['req_time'],
                            current_location=container['current_location'],
                            fulfillment_type='auto_cleanup'
                        )
                        
                        if history_logged:
                            # Only delete from REQUESTS if history logging succeeded
                            cursor.execute("DELETE FROM REQUESTS WHERE req_id = ?", (container['req_id'],))
                            logger.info(f"✅ Removed container {container['serial_no']} from requests (moved to {container['current_location']})")
                        else:
                            logger.warning(f"⚠️ Skipped deleting container {container['serial_no']} due to history logging failure")
                            
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
        try:
            logger.info("📋 Fetching production locations...")
            prod_locations = await get_prod_locations()
            results['prod_locations'] = prod_locations
            logger.info(f"✅ Found {len(prod_locations)} production locations")
        except Exception as e:
            error_msg = f"Error fetching production locations: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'checked_requests': 0,
                'removed_containers': 0
            }
        
        # Get active requests
        try:
            logger.info("🗄️ Fetching active requests from database...")
            with AzureSQLConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT req_id, serial_no, part_no, revision, quantity, location, deliver_to, req_time 
                    FROM REQUESTS 
                    ORDER BY req_time DESC
                """)
                active_requests = cursor.fetchall()
                
            results['checked_requests'] = len(active_requests)
            logger.info(f"📊 Found {len(active_requests)} active requests to check")
        except Exception as e:
            error_msg = f"Error fetching active requests from database: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'checked_requests': 0,
                'removed_containers': 0
            }
        
        containers_to_remove = []
        
        # Check each request
        for req_id, serial_no, part_no, revision, quantity, stored_location, deliver_to, req_time in active_requests:
            try:
                current_location = await check_container_current_location(serial_no)
                
                if current_location and current_location in prod_locations:
                    container_info = {
                        'req_id': req_id,
                        'serial_no': serial_no,
                        'part_no': part_no,
                        'revision': revision,
                        'quantity': float(quantity) if quantity is not None else 0.0,
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
                        # Convert req_time back to datetime if it's a string
                        req_time_dt = container['req_time']
                        if isinstance(req_time_dt, str):
                            try:
                                req_time_dt = datetime.fromisoformat(req_time_dt)
                            except:
                                req_time_dt = datetime.now()  # Fallback
                        
                        # Log to history before deleting
                        history_logged = log_request_to_history(
                            req_id=container['req_id'],
                            serial_no=container['serial_no'],
                            part_no=container['part_no'],
                            revision=container['revision'] or '',
                            quantity=float(container['quantity']) if container['quantity'] else 0.0,
                            location=container['stored_location'],
                            deliver_to=container['deliver_to'],
                            req_time=req_time_dt,
                            current_location=container['current_location'],
                            fulfillment_type='manual_cleanup'
                        )
                        
                        if history_logged:
                            cursor.execute("DELETE FROM REQUESTS WHERE req_id = ?", (container['req_id'],))
                        else:
                            error_msg = f"Failed to log container {container['serial_no']} to history, skipping deletion"
                            results['errors'].append(error_msg)
                            
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

async def automated_history_cleanup():
    """
    Automated function to clean up history records older than 30 days
    Runs daily to maintain database performance
    """
    try:
        logger.info("🧹 Starting automated history cleanup...")
        
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            
            # Count records that will be deleted
            cursor.execute("""
                SELECT COUNT(*) 
                FROM REQUESTS_HISTORY 
                WHERE fulfilled_time < DATEADD(day, -30, GETDATE())
            """)
            records_to_delete = cursor.fetchone()[0]
            
            if records_to_delete > 0:
                # Delete records older than 30 days
                cursor.execute("""
                    DELETE FROM REQUESTS_HISTORY 
                    WHERE fulfilled_time < DATEADD(day, -30, GETDATE())
                """)
                conn.commit()
                
                logger.info(f"✅ Cleaned up {records_to_delete} old history records (>30 days)")
            else:
                logger.info("✅ No old history records to clean up")
                
        # Get current statistics after cleanup
        cursor.execute("SELECT COUNT(*) FROM REQUESTS_HISTORY")
        remaining_records = cursor.fetchone()[0]
        logger.info(f"📊 History table now contains {remaining_records} records")
        
    except Exception as e:
        logger.error(f"❌ Error in automated history cleanup: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

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
            
            # Parse the req_time from ISO string and ensure it's stored consistently
            req_time_str = data['req_time']
            try:
                # Parse ISO string to datetime object
                req_time = datetime.fromisoformat(req_time_str.replace('Z', '+00:00'))
                # Convert to UTC if it has timezone info, otherwise assume it's already UTC
                if req_time.tzinfo is not None:
                    req_time_utc = req_time.astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    req_time_utc = req_time
            except:
                # Fallback to current UTC time if parsing fails
                req_time_utc = datetime.utcnow()
                
            print(f"Original req_time: {req_time_str}, Stored as UTC: {req_time_utc}")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO REQUESTS (req_id, serial_no, part_no, revision, quantity, location, deliver_to, req_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (req_id, serial_no, part_no, data['revision'], data['quantity'], data['location'], data['workcenter'], req_time_utc))
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

@app.get("/history", response_class=HTMLResponse)
async def get_history_view(request: Request):
    """
    History view for displaying fulfilled request analytics and history log
    """
    return templates.TemplateResponse("history.html", {
        "request": request
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
            
            # First, get the request data before deleting for history logging
            cursor.execute("""
                SELECT req_id, serial_no, part_no, revision, quantity, location, deliver_to, req_time 
                FROM REQUESTS 
                WHERE serial_no = ?
            """, (serial_no,))
            request_data = cursor.fetchone()
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Request not found")
            
            # Extract the request data
            req_id, serial_no_db, part_no, revision, quantity, location, deliver_to, req_time = request_data
            
            # Log to history before deleting (manual delete - no current_location since we don't know where it went)
            history_logged = log_request_to_history(
                req_id=req_id,
                serial_no=serial_no_db,
                part_no=part_no,
                revision=revision or '',
                quantity=float(quantity) if quantity else 0.0,
                location=location,
                deliver_to=deliver_to,
                req_time=req_time,
                current_location='Unknown (Manual Delete)',
                fulfillment_type='manual_delete'
            )
            
            if not history_logged:
                logger.warning(f"⚠️ Failed to log request {serial_no} to history, but proceeding with deletion")
            
            # Delete from REQUESTS table
            cursor.execute("DELETE FROM REQUESTS WHERE serial_no = ?", (serial_no,))
            conn.commit()
            
            logger.info(f"🗑️ Manual delete: Request {serial_no} removed by user")
            return JSONResponse(content={"message": "Request deleted successfully"})
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Error deleting request {serial_no}: {e}")
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
        logger.info(f"✅ Manual cleanup completed with status: {results.get('status', 'unknown')}")
        
        # Use jsonable_encoder to handle any serialization issues (like Decimal objects)
        serializable_results = jsonable_encoder(results)
        
        # Return appropriate HTTP status based on results
        if results.get('status') == 'error':
            return JSONResponse(content=serializable_results, status_code=500)
        else:
            return JSONResponse(content=serializable_results, status_code=200)
            
    except Exception as e:
        logger.error(f"❌ Error in manual cleanup API: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        
        # Return a more detailed error response
        error_response = {
            'status': 'error',
            'message': f"Internal server error: {str(e)}",
            'error_type': type(e).__name__,
            'checked_requests': 0,
            'removed_containers': 0
        }
        return JSONResponse(content=jsonable_encoder(error_response), status_code=500)

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

# --- History API Endpoints ---

@app.get("/api/history", response_class=JSONResponse)
async def get_history(
    page: int = 1,
    limit: int = 50,
    serial_no: Optional[str] = None,
    part_no: Optional[str] = None,
    fulfillment_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get paginated history of fulfilled requests with optional filtering
    """
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 500:  # Max 500 records per page
            limit = 50
            
        offset = (page - 1) * limit
        
        # Build WHERE clause with filters
        where_clauses = ["fulfilled_time >= DATEADD(day, -30, GETDATE())"]  # Only last 30 days
        # Exclude TEST workcenter/deliver_to from history display
        where_clauses.append("deliver_to != 'TEST'")
        params = []
        
        if serial_no:
            where_clauses.append("serial_no LIKE ?")
            params.append(f"%{serial_no}%")
            
        if part_no:
            where_clauses.append("part_no LIKE ?")
            params.append(f"%{part_no}%")
            
        if fulfillment_type:
            where_clauses.append("fulfillment_type = ?")
            params.append(fulfillment_type)
            
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                where_clauses.append("fulfilled_time >= ?")
                params.append(start_dt)
            except:
                pass  # Invalid date format, skip filter
                
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                where_clauses.append("fulfilled_time <= ?")
                params.append(end_dt)
            except:
                pass  # Invalid date format, skip filter
        
        where_clause = " AND ".join(where_clauses)
        
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            
            # Get total count for pagination info
            count_sql = f"SELECT COUNT(*) FROM REQUESTS_HISTORY WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            data_sql = f"""
                SELECT history_id, req_id, serial_no, part_no, revision, quantity, 
                       location, deliver_to, req_time, fulfilled_time, 
                       fulfillment_duration_minutes, fulfillment_type, current_location
                FROM REQUESTS_HISTORY 
                WHERE {where_clause}
                ORDER BY fulfilled_time DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            cursor.execute(data_sql, params + [offset, limit])
            
            columns = [column[0] for column in cursor.description]
            history_records = []
            
            for row in cursor.fetchall():
                record = {}
                for i, value in enumerate(row):
                    if isinstance(value, datetime):
                        # Convert datetime fields to Czech timezone
                        if columns[i] in ['req_time', 'fulfilled_time']:
                            record[columns[i]] = convert_to_czech_timezone(value)
                        else:
                            record[columns[i]] = value.isoformat()
                    elif isinstance(value, Decimal):
                        record[columns[i]] = float(value)
                    else:
                        record[columns[i]] = value
                history_records.append(record)
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            
            return JSONResponse(content={
                'data': history_records,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_records': total_count,
                    'limit': limit,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters': {
                    'serial_no': serial_no,
                    'part_no': part_no,
                    'fulfillment_type': fulfillment_type,
                    'start_date': start_date,
                    'end_date': end_date
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/stats", response_class=JSONResponse)
async def get_history_stats(
    days: int = 30,
    part_no: Optional[str] = None
):
    """
    Get fulfillment statistics and analytics for the specified period (in days)
    Fulfillment durations are tracked in minutes
    """
    try:
        # Validate days parameter
        if days < 1 or days > 365:  # Max 1 year
            days = 30
            
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_clauses = [f"fulfilled_time >= DATEADD(day, -{days}, GETDATE())"]
            # Exclude TEST workcenter/deliver_to from calculations
            where_clauses.append("deliver_to != 'TEST'")
            params = []
            
            if part_no:
                where_clauses.append("part_no = ?")
                params.append(part_no)
                
            where_clause = " AND ".join(where_clauses)
            
            # Overall statistics (exclude manual_delete from performance calculations)
            cursor.execute(f"""
                SELECT 
                    COUNT(CASE WHEN fulfillment_type != 'manual_delete' THEN 1 END) as total_fulfilled,
                    AVG(CASE WHEN fulfillment_type != 'manual_delete' THEN CAST(fulfillment_duration_minutes AS FLOAT) END) as avg_fulfillment_minutes,
                    MIN(CASE WHEN fulfillment_type != 'manual_delete' THEN fulfillment_duration_minutes END) as min_fulfillment_minutes,
                    MAX(CASE WHEN fulfillment_type != 'manual_delete' THEN fulfillment_duration_minutes END) as max_fulfillment_minutes,
                    COUNT(CASE WHEN fulfillment_type = 'auto_cleanup' THEN 1 END) as auto_fulfilled,
                    COUNT(CASE WHEN fulfillment_type = 'manual_cleanup' THEN 1 END) as manual_cleanup,
                    COUNT(CASE WHEN fulfillment_type = 'manual_delete' THEN 1 END) as manual_delete
                FROM REQUESTS_HISTORY
                WHERE {where_clause}
            """, params)
            overall_stats = cursor.fetchone()
            
            # Statistics by part number (exclude manual_delete from performance calculations)
            cursor.execute(f"""
                SELECT 
                    part_no,
                    COUNT(CASE WHEN fulfillment_type != 'manual_delete' THEN 1 END) as fulfilled_count,
                    AVG(CASE WHEN fulfillment_type != 'manual_delete' THEN CAST(fulfillment_duration_minutes AS FLOAT) END) as avg_fulfillment_minutes,
                    MIN(CASE WHEN fulfillment_type != 'manual_delete' THEN fulfillment_duration_minutes END) as min_fulfillment_minutes,
                    MAX(CASE WHEN fulfillment_type != 'manual_delete' THEN fulfillment_duration_minutes END) as max_fulfillment_minutes
                FROM REQUESTS_HISTORY
                WHERE {where_clause}
                GROUP BY part_no
                HAVING COUNT(CASE WHEN fulfillment_type != 'manual_delete' THEN 1 END) > 0
                ORDER BY fulfilled_count DESC, avg_fulfillment_minutes ASC
            """, params)
            part_stats = cursor.fetchall()
            
            # Daily fulfillment trend (last 7 days for performance, exclude manual_delete)
            trend_days = min(days, 7)
            cursor.execute(f"""
                SELECT 
                    CAST(fulfilled_time AS DATE) as fulfillment_date,
                    COUNT(CASE WHEN fulfillment_type != 'manual_delete' THEN 1 END) as fulfilled_count,
                    AVG(CASE WHEN fulfillment_type != 'manual_delete' THEN CAST(fulfillment_duration_minutes AS FLOAT) END) as avg_duration
                FROM REQUESTS_HISTORY
                WHERE fulfilled_time >= DATEADD(day, -{trend_days}, GETDATE()) AND deliver_to != 'TEST'
                {(" AND " + " AND ".join(where_clauses[2:])) if len(where_clauses) > 2 else ""}
                GROUP BY CAST(fulfilled_time AS DATE)
                HAVING COUNT(CASE WHEN fulfillment_type != 'manual_delete' THEN 1 END) > 0
                ORDER BY fulfillment_date DESC
            """, params[1:] if part_no else [])
            daily_trend = cursor.fetchall()
            
            # Performance categories (fast, medium, slow, exclude manual_delete)
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN fulfillment_duration_minutes <= 60 THEN 'Fast (≤1 hour)'
                        WHEN fulfillment_duration_minutes <= 480 THEN 'Medium (1-8 hours)'
                        WHEN fulfillment_duration_minutes <= 1440 THEN 'Slow (8-24 hours)'
                        ELSE 'Very Slow (>24 hours)'
                    END as performance_category,
                    COUNT(*) as count,
                    AVG(CAST(fulfillment_duration_minutes AS FLOAT)) as avg_minutes
                FROM REQUESTS_HISTORY
                WHERE {where_clause} AND fulfillment_type != 'manual_delete'
                GROUP BY 
                    CASE 
                        WHEN fulfillment_duration_minutes <= 60 THEN 'Fast (≤1 hour)'
                        WHEN fulfillment_duration_minutes <= 480 THEN 'Medium (1-8 hours)'
                        WHEN fulfillment_duration_minutes <= 1440 THEN 'Slow (8-24 hours)'
                        ELSE 'Very Slow (>24 hours)'
                    END
                ORDER BY avg_minutes ASC
            """, params)
            performance_categories = cursor.fetchall()
            
            # Get all history records for shift analysis (exclude manual_delete)
            cursor.execute(f"""
                SELECT fulfilled_time, fulfillment_duration_minutes, fulfillment_type
                FROM REQUESTS_HISTORY
                WHERE {where_clause} AND fulfillment_type != 'manual_delete'
            """, params)
            shift_raw_data = cursor.fetchall()
            
            # Calculate shift-based statistics
            shift_data = {'Morning': [], 'Evening': [], 'Night': []}
            
            for row in shift_raw_data:
                fulfilled_time, duration_minutes, fulfillment_type = row
                shift = get_shift_from_czech_datetime(fulfilled_time)
                if shift in shift_data:
                    shift_data[shift].append({
                        'duration': duration_minutes,
                        'type': fulfillment_type
                    })
            
            by_shift = []
            for shift_name, records in shift_data.items():
                if records:
                    durations = [r['duration'] for r in records]
                    auto_count = sum(1 for r in records if r['type'] == 'auto_cleanup')
                    manual_cleanup_count = sum(1 for r in records if r['type'] == 'manual_cleanup')
                    manual_delete_count = sum(1 for r in records if r['type'] == 'manual_delete')
                    
                    by_shift.append({
                        'shift': shift_name,
                        'time_range': 'Morning (6:00-14:00)' if shift_name == 'Morning' 
                                     else 'Evening (14:00-22:00)' if shift_name == 'Evening' 
                                     else 'Night (22:00-6:00)',
                        'fulfilled_count': len(records),
                        'avg_fulfillment_minutes': round(sum(durations) / len(durations), 2),
                        'avg_fulfillment_hours': round((sum(durations) / len(durations)) / 60, 2),
                        'min_fulfillment_minutes': min(durations),
                        'max_fulfillment_minutes': max(durations),
                        'auto_fulfilled': auto_count,
                        'manual_cleanup': manual_cleanup_count,
                        'manual_delete': manual_delete_count
                    })
                else:
                    by_shift.append({
                        'shift': shift_name,
                        'time_range': 'Morning (6:00-14:00)' if shift_name == 'Morning' 
                                     else 'Evening (14:00-22:00)' if shift_name == 'Evening' 
                                     else 'Night (22:00-6:00)',
                        'fulfilled_count': 0,
                        'avg_fulfillment_minutes': 0,
                        'avg_fulfillment_hours': 0,
                        'min_fulfillment_minutes': 0,
                        'max_fulfillment_minutes': 0,
                        'auto_fulfilled': 0,
                        'manual_cleanup': 0,
                        'manual_delete': 0
                    })
            
            # Sort by shift order: Morning, Evening, Night
            shift_order = {'Morning': 0, 'Evening': 1, 'Night': 2}
            by_shift.sort(key=lambda x: shift_order.get(x['shift'], 3))
            
            # Format results
            overall = {
                'total_fulfilled': overall_stats[0] if overall_stats else 0,
                'avg_fulfillment_minutes': round(overall_stats[1], 2) if overall_stats and overall_stats[1] else 0,
                'avg_fulfillment_hours': round(overall_stats[1] / 60, 2) if overall_stats and overall_stats[1] else 0,
                'min_fulfillment_minutes': overall_stats[2] if overall_stats else 0,
                'max_fulfillment_minutes': overall_stats[3] if overall_stats else 0,
                'auto_fulfilled': overall_stats[4] if overall_stats else 0,
                'manual_cleanup': overall_stats[5] if overall_stats else 0,
                'manual_delete': overall_stats[6] if overall_stats else 0
            }
            
            by_part_number = []
            for row in part_stats:
                by_part_number.append({
                    'part_no': row[0],
                    'fulfilled_count': row[1],
                    'avg_fulfillment_minutes': round(row[2], 2) if row[2] else 0,
                    'avg_fulfillment_hours': round(row[2] / 60, 2) if row[2] else 0,
                    'min_fulfillment_minutes': row[3],
                    'max_fulfillment_minutes': row[4]
                })
            
            daily_trends = []
            for row in daily_trend:
                daily_trends.append({
                    'date': row[0].isoformat() if row[0] else None,
                    'fulfilled_count': row[1],
                    'avg_duration_minutes': round(row[2], 2) if row[2] else 0,
                    'avg_duration_hours': round(row[2] / 60, 2) if row[2] else 0
                })
            
            performance_breakdown = []
            for row in performance_categories:
                performance_breakdown.append({
                    'category': row[0],
                    'count': row[1],
                    'avg_minutes': round(row[2], 2) if row[2] else 0,
                    'percentage': round((row[1] / overall['total_fulfilled']) * 100, 1) if overall['total_fulfilled'] > 0 else 0
                })
            
            return JSONResponse(content={
                'period_days': days,
                'part_no_filter': part_no,
                'overall': overall,
                'by_part_number': by_part_number,
                'by_shift': by_shift,
                'daily_trends': daily_trends,
                'performance_breakdown': performance_breakdown,
                'generated_at': datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error getting history stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/clear-all", response_class=JSONResponse)
async def clear_all_history():
    """
    Delete all records from the REQUESTS_HISTORY table
    This is a destructive operation and should be used with caution
    """
    try:
        with AzureSQLConnection() as conn:
            cursor = conn.cursor()
            
            # Count records before deletion
            cursor.execute("SELECT COUNT(*) FROM REQUESTS_HISTORY")
            count_before = cursor.fetchone()[0]
            
            if count_before == 0:
                return JSONResponse(content={
                    'status': 'success',
                    'message': 'History was already empty',
                    'deleted_count': 0
                })
            
            # Delete all records
            cursor.execute("DELETE FROM REQUESTS_HISTORY")
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"🗑️ Cleared all history: {deleted_count} records deleted")
            
            return JSONResponse(content={
                'status': 'success',
                'message': f'Successfully deleted all history records',
                'deleted_count': deleted_count
            })
            
    except Exception as e:
        logger.error(f"❌ Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")
