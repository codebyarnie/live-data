# Quick Start Guide - NinjaTrader to FastAPI

## For First-Time Users: Start Here!

### Step 1: Test NinjaTrader Basic Functionality

Before using the full DataFeederStrategy, verify NinjaTrader is working:

1. **Copy the test strategy:**
   ```
   Copy: ninjatrader/SimpleTestStrategy.cs
   To: Documents\NinjaTrader 8\bin\Custom\Strategies\
   ```

2. **Open NinjaTrader and compile:**
   - Press **F3** (NinjaScript Editor)
   - Press **F5** (Compile)
   - Look for "Compiled successfully" in the Output tab

3. **Apply to a chart:**
   - Open any chart with live data
   - Right-click → Strategies
   - Add "SimpleTestStrategy"
   - Click OK

4. **Check for output:**
   - Press **F5** to open Output window
   - You should see:
   ```
   ========================================
   SimpleTestStrategy: LOADED SUCCESSFULLY
   ========================================
   SimpleTestStrategy: NOW RUNNING IN REAL-TIME
   Bar #1: Time=12/04 10:30:00, Close=$4825.5, Volume=1250
   ```

5. **Look for green arrow:**
   - Top-left of chart should show green arrow with "SimpleTestStrategy"

✅ **If this works, proceed to Step 2**
❌ **If this doesn't work, see TROUBLESHOOTING.md**

---

### Step 2: Start FastAPI Backend

1. **Open a terminal/command prompt**

2. **Navigate to backend folder:**
   ```bash
   cd ninjatrader-fastapi-integration/backend
   ```

3. **Install dependencies (first time only):**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server:**
   ```bash
   python main.py
   ```

5. **Verify it's running:**
   You should see:
   ```
   Starting NinjaTrader FastAPI Data Receiver...
   Server will be available at: http://localhost:8000
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

6. **Test in browser:**
   Open: http://localhost:8000

   Should see:
   ```json
   {
     "status": "running",
     "service": "NinjaTrader Data Receiver",
     "timestamp": "2024-12-04T10:30:15.123456"
   }
   ```

✅ **Backend is ready!**

---

### Step 3: Install DataFeederStrategy

1. **Copy the main strategy:**
   ```
   Copy: ninjatrader/DataFeederStrategy.cs
   To: Documents\NinjaTrader 8\bin\Custom\Strategies\
   ```

2. **Compile in NinjaTrader:**
   - F3 (NinjaScript Editor)
   - F5 (Compile)
   - Check for "Compiled successfully"

3. **If compilation fails:**
   - See TROUBLESHOOTING.md → "Check for Compilation Errors"
   - Most common: Missing Newtonsoft.Json reference

---

### Step 4: Run the Full Integration

1. **Make sure FastAPI is running** (from Step 2)

2. **Open a NinjaTrader chart** with live data

3. **Apply DataFeederStrategy:**
   - Right-click chart → Strategies
   - Add "DataFeederStrategy"
   - Configure if needed:
     - API Endpoint: `http://localhost:8000/data` (default)
     - Update Interval: `1` second (default)
   - Click OK

4. **Look for green arrow** on chart

5. **Check NinjaTrader Output (F5):**
   ```
   =========================================
   DataFeederStrategy: STARTED
   Instrument: ES 03-25
   API Endpoint: http://localhost:8000/data
   Update Interval: 1 seconds
   =========================================
   DataFeederStrategy: NOW IN REAL-TIME MODE
   Data will be sent to FastAPI backend
   =========================================
   Attempting to send data #1...
   ✓ Data #1 sent successfully: ES 03-25 @ 4825.5
   ```

6. **Check FastAPI Console:**
   ```
   ================================================================================
   [2024-12-04 10:30:15.123] Received data from NinjaTrader:
     Symbol: ES 03-25
     Timestamp: 2024-12-04T10:30:15
     Price: $4825.50
     Volume: 1250.0
     Bid: $4825.25
     Ask: $4825.50
   ================================================================================
   ```

✅ **Success! Data is flowing from NinjaTrader to FastAPI!**

---

## What You Should See

### In NinjaTrader:
- ✅ Green arrow on chart
- ✅ Output window showing "Data sent successfully"
- ✅ No error messages

### In FastAPI Console:
- ✅ Data being logged every second (or your configured interval)
- ✅ Formatted market data with prices, volume, etc.

---

## Common Issues

### No green arrow in NinjaTrader
👉 See TROUBLESHOOTING.md → "No Green Arrow"

### Green arrow but no output
👉 Check Output window settings (Tools → Output Window → Gear icon → Enable "Scripts")

### Output shows "HTTP Error"
👉 Make sure FastAPI backend is running (`python main.py`)

### Compilation errors
👉 See TROUBLESHOOTING.md → "Check for Compilation Errors"

### Data not appearing in FastAPI console
👉 Check if NinjaTrader output shows "Data sent successfully"
👉 Check FastAPI console isn't frozen (try scrolling)

---

## Next Steps

Once everything is working:

1. **Adjust update interval** if needed:
   - Right-click chart → Strategies → Configure
   - Change "Update Interval" to 5 or 10 seconds if 1 second is too frequent

2. **Monitor multiple instruments:**
   - Apply the strategy to multiple charts
   - Each will send data independently

3. **Extend the FastAPI backend:**
   - Store data in a database
   - Add data analysis
   - Create visualizations
   - Build a web dashboard

4. **Customize the strategy:**
   - Edit DataFeederStrategy.cs
   - Add more data fields
   - Implement custom logic
   - Add filters for specific conditions

---

## File Locations Reference

```
NinjaTrader Strategy Files:
  Documents\NinjaTrader 8\bin\Custom\Strategies\DataFeederStrategy.cs
  Documents\NinjaTrader 8\bin\Custom\Strategies\SimpleTestStrategy.cs

NinjaTrader Output Window:
  Press F5 in NinjaTrader or Tools → Output Window

FastAPI Backend:
  ninjatrader-fastapi-integration/backend/main.py
```

---

## Getting Help

1. **No output in NinjaTrader?**
   - Try SimpleTestStrategy first
   - Check Output window settings
   - See TROUBLESHOOTING.md

2. **Compilation errors?**
   - See TROUBLESHOOTING.md → Compilation section
   - Check References in NinjaScript Editor

3. **Connection errors?**
   - Verify FastAPI is running: http://localhost:8000
   - Check firewall settings
   - Verify API endpoint URL in strategy parameters

---

**Need more help?** See **TROUBLESHOOTING.md** for detailed solutions.
