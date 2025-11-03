# Drop List Application

A warehouse management system for tracking and managing container return requests from workcenters to the warehouse with real-time updates and ERP integration.

## Features

- **Container Return Management**: Track containers being returned from workcenters by serial number
- **ERP Integration**: Seamless integration with Plex ERP system
- **Real-time Updates**: WebSocket support for live return request notifications
- **Database Persistence**: Azure SQL Database for reliable data storage
- **Web Interface**: User-friendly interface for warehouse return operations
- **REST API**: Complete API for programmatic access
- **Simplified Workflow**: Operators only need to specify serial number and master unit

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: Azure SQL Database
- **Frontend**: HTML/CSS/JavaScript
- **ERP**: Plex Manufacturing Cloud
- **Real-time**: WebSocket connections
- **Containerization**: Docker support

## Prerequisites

- Python 3.8+
- Azure SQL Database instance
- Plex ERP system access

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Drop List"
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file with:
   ```
   AZURE_SQL_SERVER=your-server-name
   AZURE_SQL_DATABASE=your-database-name
   AZURE_SQL_USERNAME=your-username
   AZURE_SQL_PASSWORD=your-password
   PORT=8000
   ```

## Database Setup

The application requires a `REQUESTS` table in your Azure SQL Database:

```sql
CREATE TABLE REQUESTS (
    req_id INT,
    serial_no NVARCHAR(255),
    part_no NVARCHAR(255),
    revision NVARCHAR(50),
    quantity DECIMAL(10,2),
    location NVARCHAR(255),
    deliver_to NVARCHAR(255),
    req_time DATETIME
);
```

## Usage

1. **Start the application**
   ```bash
   python main.py
   ```

2. **Access the web interface**
   Open your browser to `http://localhost:8000`

3. **Using Docker**
   ```bash
   docker build -t drop-list .
   docker run -p 8000:8000 drop-list
   ```

## API Endpoints

### Core Operations
- `GET /` - Main web interface
- `POST /part/{part_no}` - Get containers for a part number
- `POST /part/{part_no}/{serial_no}` - Request a specific serial number
- `GET /requests` - Driver interface for viewing requests

### Data Management
- `GET /api/requests` - Retrieve all requests (JSON)
- `DELETE /api/requests/{serial_no}` - Delete a request
- `GET /barcode/{location}` - Get barcode for location

### Real-time Communication
- `WebSocket /ws` - Real-time updates

## Project Structure

```
Drop List/
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── .env                # Environment configuration
├── templates/          # HTML templates
│   ├── index.html      # Main interface
│   └── driver.html     # Driver interface
├── static/            # Static assets
│   ├── assets/        # Images and icons
│   ├── *.css          # Stylesheets
│   └── *.js           # JavaScript files
└── venv/              # Virtual environment
```

## Configuration

The application connects to:
- **Azure SQL Database**: For persistent storage
- **Plex ERP System**: For inventory data retrieval
- **Production Storage Locations**: Filtered inventory locations

## Development

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Run in development mode**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary to Vintech CZ.

## Support

For technical support or questions, contact the development team.