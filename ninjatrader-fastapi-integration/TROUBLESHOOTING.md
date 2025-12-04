# NinjaTrader DataFeeder Strategy - Troubleshooting Guide

## No Green Arrow / Strategy Not Showing as Enabled

### Step 1: Check for Compilation Errors

1. Open **NinjaTrader 8**
2. Press **F3** (or Tools → NinjaScript Editor)
3. Press **F5** to compile
4. Look at the **Output** tab at the bottom
5. Check for any errors (shown in red)

**Common Compilation Errors:**

#### Error: "Newtonsoft.Json does not exist"
**Solution:**
```
1. In NinjaScript Editor, click Tools → References
2. Check if "Newtonsoft.Json" is listed
3. If not, click "Add" → Browse to NinjaTrader installation folder
4. Navigate to: C:\Program Files\NinjaTrader 8\bin\
5. Select "Newtonsoft.Json.dll"
6. Click OK and recompile (F5)
```

#### Error: "HttpClient does not exist"
**Solution:**
```
1. In NinjaScript Editor, click Tools → References
2. Ensure these are checked:
   - System.Net.Http
   - System.Threading
3. Click OK and recompile (F5)
```

### Step 2: Verify Strategy Loaded Successfully

After successful compilation, check the **Output** tab for:
```
Compiled successfully.
```

### Step 3: Apply Strategy to Chart

1. Open a **live chart** (not replay/historical)
2. Make sure you have a **data connection** (green connection indicator in bottom right)
3. Right-click on the chart → **Strategies**
4. In the left list, you should see **DataFeederStrategy**
5. Select it and click **Add** (or double-click it)
6. Click **OK**

### Step 4: Look for the Enabled Indicator

Once enabled, you should see:
- **Green arrow** on the top-left of the chart with "DataFeederStrategy" label
- If you see a **red cross** instead, the strategy has stopped due to an error

### Step 5: Check NinjaScript Output Window

Open the **Output** window (Tools → Output Window, or F5)

**What you should see immediately:**
```
DataFeederStrategy: SetDefaults completed
DataFeederStrategy: Configuring...
DataFeederStrategy: Configuration completed
=========================================
DataFeederStrategy: STARTED
Instrument: ES 03-25
API Endpoint: http://localhost:8000/data
Update Interval: 1 seconds
Waiting for bars to load...
=========================================
DataFeederStrategy: Processing historical data...
Bar 1: Time=12/04/2024 10:00:00, Close=4825.5, State=Historical
Bar 2: Time=12/04/2024 10:01:00, Close=4826.0, State=Historical
DataFeederStrategy: Transitioning to real-time...
=========================================
DataFeederStrategy: NOW IN REAL-TIME MODE
Data will be sent to FastAPI backend
=========================================
```

## If You See No Output at All

### Problem: Strategy doesn't appear in the Strategies list

**Solutions:**

1. **Check the namespace:**
   - Open the .cs file
   - Verify line 27 says: `namespace NinjaTrader.NinjaScript.Strategies`
   - Must be exactly this, not a custom namespace

2. **Verify file location:**
   ```
   Documents\NinjaTrader 8\bin\Custom\Strategies\DataFeederStrategy.cs
   ```

3. **Reload NinjaScript:**
   - File → Utilities → Reload All NinjaScript

4. **Restart NinjaTrader:**
   - Close NinjaTrader completely
   - Reopen and try again

### Problem: Strategy appears but won't enable

**Check these:**

1. **Chart Type:** Strategy requires a bars-based chart
   - Won't work on: Market Depth, Volume Profile, etc.
   - Will work on: Minute, Second, Tick, Volume bars

2. **Data Connection:** Verify you're connected to data feed
   - Check connection indicator (bottom-right corner)
   - Should be green, not red or gray

3. **Instrument:** Make sure the chart has an instrument loaded
   - Can't be a blank chart

## Strategy Enables but No Output

### Check Output Window Settings

1. Go to **Tools → Output Window**
2. Click the **gear icon** (settings)
3. Make sure **"Scripts"** logging is enabled
4. Set verbosity to **"Information"** or **"Debug"**

### Enable Strategy on a Real-Time Chart

The strategy prints different messages depending on the state:
- **Historical data:** Prints first 3 bars only
- **Real-time:** Prints data sending attempts

**To ensure real-time:**
1. Use a **live data connection** (not Replay or Playback)
2. Open a chart with **real-time data**
3. Apply the strategy

## Common Error Messages and Solutions

### "HTTP Error: Unable to connect to the remote server"

**Problem:** FastAPI backend is not running

**Solution:**
```bash
# Start the FastAPI server first
cd ninjatrader-fastapi-integration/backend
python main.py
```

### "Request timeout"

**Problem:** Network issues or FastAPI server is slow/hung

**Solutions:**
1. Check if FastAPI server console shows the request
2. Try increasing timeout in line 70 of DataFeederStrategy.cs:
   ```csharp
   httpClient.Timeout = TimeSpan.FromSeconds(10); // increased from 5
   ```

### "Failed to send data. HTTP Status: 404"

**Problem:** Wrong API endpoint URL

**Solution:**
1. Right-click chart → Strategies
2. Select DataFeederStrategy → Configure
3. Check "API Endpoint" parameter
4. Should be: `http://localhost:8000/data` (note the `/data` at the end)

### "Previous request still in progress"

**Problem:** API responses are slow, requests backing up

**Solutions:**
1. Increase "Update Interval" parameter (try 5 or 10 seconds)
2. Check FastAPI server performance
3. Reduce chart update frequency (use larger bar size)

## Debug Checklist

Use this checklist to verify everything:

- [ ] NinjaTrader 8 is open and connected to data feed
- [ ] Compiled successfully (F5 in NinjaScript Editor, no errors)
- [ ] Strategy file is in correct location (`Documents\NinjaTrader 8\bin\Custom\Strategies\`)
- [ ] FastAPI backend is running (`python main.py`)
- [ ] FastAPI server shows "Uvicorn running on http://0.0.0.0:8000"
- [ ] Chart is open with real-time data (not historical replay)
- [ ] Chart type is bars-based (minute, second, tick, volume)
- [ ] Strategy is applied to chart (right-click → Strategies → Add DataFeederStrategy)
- [ ] Green arrow appears on chart (if red X, check output for errors)
- [ ] Output window is open (F5) and set to show "Scripts" logs
- [ ] Output window shows startup messages from DataFeederStrategy

## Testing the Setup

### Test 1: Verify FastAPI Backend

Open browser, go to: `http://localhost:8000`

Should see:
```json
{
  "status": "running",
  "service": "NinjaTrader Data Receiver",
  "timestamp": "2024-12-04T10:30:15.123456"
}
```

### Test 2: Manual API Test

Test the API manually using PowerShell:
```powershell
$body = @{
    symbol = "TEST"
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    price = 100.50
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/data" -Method Post -Body $body -ContentType "application/json"
```

You should see the data printed in the FastAPI console.

### Test 3: Verify NinjaTrader Output

If the strategy is enabled, you should see output even if the API isn't connected.

**Expected output in NinjaTrader Output window:**
```
DataFeederStrategy: STARTED
DataFeederStrategy: NOW IN REAL-TIME MODE
Attempting to send data #1...
✗ HTTP Error: Unable to connect to the remote server
  → Is the FastAPI server running on http://localhost:8000/data?
```

This confirms the strategy is running (even though API isn't reachable).

## Still Having Issues?

### Capture Detailed Logs

1. In NinjaScript Editor, add more Print statements
2. Recompile (F5)
3. Disable and re-enable the strategy
4. Copy all output from Output window
5. Review for error messages

### Create a Minimal Test Strategy

Try this minimal strategy to verify basic functionality:

```csharp
public class TestStrategy : Strategy
{
    protected override void OnStateChange()
    {
        if (State == State.SetDefaults)
        {
            Name = "TestStrategy";
            Print("TestStrategy loaded!");
        }
    }

    protected override void OnBarUpdate()
    {
        if (CurrentBar < 1) return;
        Print($"Bar: {Time[0]}, Close: {Close[0]}");
    }
}
```

If this works but DataFeederStrategy doesn't, the issue is likely with HTTP client or JSON serialization.

## Contact Information

If you've tried all troubleshooting steps and still have issues, provide:
1. NinjaTrader version
2. Full Output window contents
3. Compilation errors (if any)
4. Whether the minimal TestStrategy works
5. FastAPI server startup output
