# NinjaTrader Chart Setup Guide

## Problem: Strategy Loads but Stops Immediately (0 Bars Processed)

If you see this output:
```
SimpleTestStrategy: LOADED SUCCESSFULLY
SimpleTestStrategy: STOPPED
Total bars processed: 0
```

This means your chart is not properly configured with data. Follow this guide to fix it.

---

## ✅ Proper Chart Setup - Step by Step

### Step 1: Verify Data Connection

1. Look at the **bottom-right corner** of NinjaTrader
2. You should see a **green connection icon**
3. If it's **red** or **gray**, you're not connected to data

**To Connect:**
- Click Connections → Connect (or press Ctrl+G)
- Choose your data provider (Kinetick, CQG, etc.)
- Wait for green connection indicator

**Using Simulated Data Feed:**
If you don't have a live data connection:
- Click Connections → Playback Connection
- This gives you simulated data for testing

### Step 2: Create a Proper Chart

#### Method A: Using New Chart (Recommended)

1. Click **File → New → Chart** (or Ctrl+N)
2. In the Chart window that opens:
   - **Instrument**: Type an instrument (examples below)
   - **Type**: Select "Minute"
   - **Value**: Enter "1" (for 1-minute bars)
   - **Days to load**: Enter "1" or "2"
3. Click **OK**

**Example Instruments to Try:**
- `ES 03-25` (E-mini S&P 500 futures)
- `NQ 03-25` (E-mini Nasdaq futures)
- `AAPL` (Apple stock)
- `MSFT` (Microsoft stock)
- `EUR/USD` (if you have forex data)

#### Method B: Using Existing Chart

If you have a chart open but no data:
1. Right-click on the chart
2. Select **Instrument** → Choose an instrument
3. Right-click again → **Data Series**
4. Verify:
   - Type: Minute (or Second, Tick, Volume)
   - Value: 1 or higher
   - Days to load: 1 or 2

### Step 3: Verify Chart Has Data

**Visual Check:**
- You should see **candlesticks or bars** on the chart
- There should be **prices** on the right axis
- There should be **times/dates** on the bottom axis

**If Chart is Empty:**
- Chart might be zoomed out too far
- Right-click → **Reload All Historical Data**
- Try a different instrument
- Check your data connection (Step 1)

### Step 4: Apply the Strategy

1. **Verify the chart has bars displayed** (see Step 3)
2. Right-click the chart → **Strategies**
3. Click **Add** (or double-click SimpleTestStrategy)
4. Click **OK**

### Step 5: Check Output

Press **F5** to open Output Window.

**You should now see:**
```
[SimpleTestStrategy] OnStateChange called - State: SetDefaults
========================================
SimpleTestStrategy: LOADED SUCCESSFULLY
========================================
[SimpleTestStrategy] OnStateChange called - State: Configure
SimpleTestStrategy: State.Configure - Configuring strategy
[SimpleTestStrategy] OnStateChange called - State: DataLoaded
========================================
SimpleTestStrategy: State.DataLoaded
  Chart Instrument: ES 03-25
  Bar Period: Minute
  Current Bars: 0
========================================
[SimpleTestStrategy] OnStateChange called - State: Historical
SimpleTestStrategy: State.Historical - Processing historical data
Bar #1: CurrentBar=0, Time=12/04 09:30:00, Close=$4825.50, Volume=1250, State=Historical
Bar #2: CurrentBar=1, Time=12/04 09:31:00, Close=$4826.00, Volume=980, State=Historical
...
[SimpleTestStrategy] OnStateChange called - State: Transition
SimpleTestStrategy: State.Transition - Moving to real-time
[SimpleTestStrategy] OnStateChange called - State: Realtime
========================================
SimpleTestStrategy: State.Realtime - NOW RUNNING IN REAL-TIME
========================================
```

---

## 🔍 Diagnosing Your Issue

Based on what you see in the Output window:

### If you see ONLY:
```
SimpleTestStrategy: LOADED SUCCESSFULLY
SimpleTestStrategy: STOPPED
```

**Problem**: Chart has no data or wrong chart type

**Solutions**:
1. Create a new chart with proper instrument (see Step 2)
2. Verify data connection (see Step 1)
3. Make sure chart type is bars-based (Minute, Second, Tick, Volume)
4. Not working: Line charts, Market Depth, or blank charts

### If you see:
```
OnStateChange called - State: SetDefaults
OnStateChange called - State: Configure
OnStateChange called - State: Terminated
```

**Problem**: Strategy is being rejected after Configure state

**Solutions**:
1. Check if chart has an instrument selected
2. Verify bars are displayed on chart
3. Try a different instrument
4. Check data connection status

### If you see bars but in State: Historical only

**Problem**: Chart is showing historical data only, not real-time

**Solutions**:
1. Verify data connection is active (green)
2. Make sure you're using a live instrument (not expired futures)
3. Check market hours - market might be closed
4. Enable "Playback Connection" for testing

---

## 📋 Quick Checklist

Before applying the strategy, verify:

- [ ] Data connection is **green** (bottom-right of NinjaTrader)
- [ ] Chart shows **bars/candlesticks** (not empty)
- [ ] Chart has an **instrument** selected (shown in top-left of chart)
- [ ] Chart type is **Minute/Second/Tick/Volume** (not Line chart)
- [ ] You can see **prices** updating (if market is open)
- [ ] "Days to load" is set to **1 or 2** (not 0)

---

## 🎯 Recommended Test Setup

For guaranteed success, use this exact setup:

### Option 1: With Live Data Connection
1. Connect to your data provider
2. New Chart (Ctrl+N):
   - Instrument: `ES 03-25` (or current ES contract)
   - Type: `Minute`
   - Value: `1`
   - Days to load: `1`
3. Wait for bars to load
4. Apply SimpleTestStrategy

### Option 2: With Playback Connection (No Live Data Needed)
1. Click **Connections → Playback Connection**
2. New Chart (Ctrl+N):
   - Instrument: `ES 03-25`
   - Type: `Minute`
   - Value: `1`
   - Days to load: `1`
3. Click **Playback → Controller**
4. Click **Play** to start simulated data
5. Apply SimpleTestStrategy

---

## 🚨 Common Mistakes

### ❌ Applying strategy to empty chart
**Fix**: Load an instrument first

### ❌ Using expired futures contracts
Example: `ES 06-24` after June 2024
**Fix**: Use current contract (e.g., `ES 03-25` for March 2025)

### ❌ Wrong chart type
Examples: Line chart, Point & Figure, Equivolume
**Fix**: Use Minute, Second, Tick, or Volume bars

### ❌ No data connection
Red or gray connection indicator
**Fix**: Connect to data provider or use Playback Connection

### ❌ Days to load = 0
Chart has no historical data to process
**Fix**: Set "Days to load" to 1 or 2

### ❌ Market is closed
Strategy might load but not receive new bars
**Fix**: Use Playback Connection for testing anytime

---

## 📸 What a Proper Chart Looks Like

A correctly configured chart should show:
- **Top-left**: Instrument name (e.g., "ES 03-25")
- **Chart area**: Bars or candlesticks
- **Right side**: Price axis with numbers
- **Bottom**: Time axis with times/dates
- **Bottom-right (NinjaTrader)**: Green connection indicator

If your chart is completely **blank/empty**, it's not configured properly.

---

## Next Steps

Once you have a chart showing bars:

1. **Copy the updated SimpleTestStrategy.cs** to your strategies folder
2. **Recompile** (F5 in NinjaScript Editor)
3. **Apply to the chart** with data
4. **Check Output window** - you should now see ALL the state transitions

**Expected output with updated strategy:**
```
[SimpleTestStrategy] OnStateChange called - State: SetDefaults
[SimpleTestStrategy] OnStateChange called - State: Configure
[SimpleTestStrategy] OnStateChange called - State: DataLoaded
[SimpleTestStrategy] OnStateChange called - State: Historical
Bar #1: CurrentBar=0, Time=12/04 09:30:00, Close=$4825.50...
```

If you still see only LOADED → STOPPED, share:
1. What instrument you're using
2. What chart type/settings
3. Connection status (green/red/gray)
