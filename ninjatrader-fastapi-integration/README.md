# NinjaTrader to FastAPI Data Integration

This solution enables real-time data streaming from NinjaTrader to a FastAPI backend. The received data is logged to the console for monitoring and debugging purposes.

## Project Structure

```
ninjatrader-fastapi-integration/
├── backend/
│   ├── main.py              # FastAPI server
│   └── requirements.txt     # Python dependencies
├── ninjatrader/
│   └── DataFeederStrategy.cs # NinjaTrader strategy
└── README.md
```

## Features

- **Real-time data streaming** from NinjaTrader to FastAPI
- **Configurable update interval** to control data flow
- **Console logging** for all received data
- **Comprehensive market data** including OHLC, volume, bid/ask
- **Async/non-blocking** design to prevent trading strategy interference
- **Error handling** and connection management

## Setup Instructions

### 1. FastAPI Backend Setup

#### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

#### Installation

1. Navigate to the backend directory:
```bash
cd ninjatrader-fastapi-integration/backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the FastAPI server:
```bash
python main.py
```

The server will start on `http://localhost:8000`

You should see:
```
Starting NinjaTrader FastAPI Data Receiver...
Server will be available at: http://localhost:8000
Send POST requests to: http://localhost:8000/data
```

#### Verify the Server

Open your browser and go to:
- `http://localhost:8000` - Health check endpoint
- `http://localhost:8000/docs` - Interactive API documentation

### 2. NinjaTrader Strategy Setup

#### Prerequisites
- NinjaTrader 8
- Newtonsoft.Json library (usually included with NinjaTrader)

#### Installation

1. **Copy the Strategy File**:
   - Copy `ninjatrader/DataFeederStrategy.cs` to your NinjaTrader scripts folder:
   - Default location: `Documents\NinjaTrader 8\bin\Custom\Strategies\`

2. **Compile in NinjaTrader**:
   - Open NinjaTrader 8
   - Go to Tools → NinjaScript Editor (or press F3)
   - Click "Compile" (or press F5)
   - Check for any compilation errors in the output window

3. **Apply the Strategy to a Chart**:
   - Open a chart for the instrument you want to monitor
   - Right-click the chart → Strategies
   - Select "DataFeederStrategy" from the list
   - Configure the parameters (optional):
     - **API Endpoint**: Default is `http://localhost:8000/data`
     - **Update Interval**: Default is 1 second
   - Click "OK" to enable the strategy

## Usage

1. **Start the FastAPI backend** (see Backend Setup above)

2. **Apply the DataFeederStrategy** to a NinjaTrader chart

3. **Monitor the console** where the FastAPI server is running

You should see output similar to:
```
================================================================================
[2024-12-04 10:30:15.123] Received data from NinjaTrader:
  Symbol: ES 03-25
  Timestamp: 2024-12-04T10:30:15
  Price: $4825.50
  Volume: 1250.0
  Bid: $4825.25
  Ask: $4825.50
  High: $4826.00
  Low: $4824.75
  Open: $4825.00
  Close: $4825.50
================================================================================
```

## Configuration

### FastAPI Backend

Edit `backend/main.py` to customize:
- **Port**: Change the `port` parameter in `uvicorn.run()` (default: 8000)
- **Host**: Change the `host` parameter (default: "0.0.0.0")
- **Logging format**: Modify the `receive_data()` function

### NinjaTrader Strategy

Configure in the strategy parameters dialog:
- **API Endpoint**: URL of your FastAPI server (default: `http://localhost:8000/data`)
- **Update Interval**: Seconds between data updates (default: 1 second)

## Data Format

The strategy sends the following data in JSON format:

```json
{
  "symbol": "ES 03-25",
  "timestamp": "2024-12-04T10:30:15",
  "price": 4825.50,
  "volume": 1250.0,
  "bid": 4825.25,
  "ask": 4825.50,
  "high": 4826.00,
  "low": 4824.75,
  "open": 4825.00,
  "close": 4825.50
}
```

## Troubleshooting

### FastAPI Server Issues

**Problem**: Cannot access `http://localhost:8000`
- **Solution**: Check if the server is running and no firewall is blocking port 8000

**Problem**: Port 8000 already in use
- **Solution**: Change the port in `main.py` and update the NinjaTrader strategy configuration

### NinjaTrader Strategy Issues

**Problem**: Strategy compilation fails
- **Solution**: Ensure Newtonsoft.Json is available. Check NinjaTrader output window for specific errors

**Problem**: "Failed to send data" messages in NinjaTrader output
- **Solution**:
  - Verify FastAPI server is running
  - Check the API endpoint URL in strategy parameters
  - Ensure no firewall is blocking the connection

**Problem**: No data appearing in console
- **Solution**:
  - Verify the strategy is enabled on the chart (green arrow indicator)
  - Check NinjaTrader output window for error messages
  - Ensure the chart is receiving live data

## Next Steps

This basic implementation logs data to the console. You can extend it to:

- **Store data in a database** (PostgreSQL, MongoDB, etc.)
- **Implement data analytics** and visualization
- **Create trading signals** based on received data
- **Build a web dashboard** to monitor data in real-time
- **Add authentication** for secure API access
- **Implement websockets** for bidirectional communication

## Requirements

### Backend
- Python 3.8+
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0

### NinjaTrader
- NinjaTrader 8
- .NET Framework 4.8
- Newtonsoft.Json

## License

This is a basic integration template. Modify and use as needed for your trading applications.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review NinjaTrader output window for error messages
3. Check FastAPI server console for error logs
