from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uvicorn

app = FastAPI(title="NinjaTrader Data Receiver")

class MarketData(BaseModel):
    """Model for market data received from NinjaTrader"""
    symbol: str
    timestamp: str
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "NinjaTrader Data Receiver",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/data")
async def receive_data(data: MarketData):
    """
    Endpoint to receive market data from NinjaTrader
    Logs the data to console
    """
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Received data from NinjaTrader:")
    print(f"  Symbol: {data.symbol}")
    print(f"  Timestamp: {data.timestamp}")
    print(f"  Price: ${data.price:.2f}")

    if data.volume is not None:
        print(f"  Volume: {data.volume}")
    if data.bid is not None:
        print(f"  Bid: ${data.bid:.2f}")
    if data.ask is not None:
        print(f"  Ask: ${data.ask:.2f}")
    if data.high is not None:
        print(f"  High: ${data.high:.2f}")
    if data.low is not None:
        print(f"  Low: ${data.low:.2f}")
    if data.open is not None:
        print(f"  Open: ${data.open:.2f}")
    if data.close is not None:
        print(f"  Close: ${data.close:.2f}")

    print("=" * 80)

    return {
        "status": "success",
        "message": "Data received and logged",
        "received_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("Starting NinjaTrader FastAPI Data Receiver...")
    print("Server will be available at: http://localhost:8000")
    print("Send POST requests to: http://localhost:8000/data")
    uvicorn.run(app, host="0.0.0.0", port=8000)
