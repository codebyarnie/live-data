# Fix: Strategy Rejected Immediately (SetDefaults → Terminated)

## Your Exact Problem

Your output shows:
```
[SimpleTestStrategy] OnStateChange called - State: SetDefaults
[SimpleTestStrategy] OnStateChange called - State: Terminated
CurrentBar at termination: -1
```

This means the strategy is being **rejected immediately** by NinjaTrader before it can even configure. The chart might show data visually, but something about the data series is incompatible with strategies.

---

## 🎯 Solution: Use the Diagnostic Indicator First

I've created a **ChartDiagnostic** indicator that's more forgiving than strategies. Let's use it to verify your chart data:

### Step 1: Install ChartDiagnostic Indicator

1. **Copy the file:**
   ```
   From: ninjatrader-fastapi-integration/ninjatrader/ChartDiagnostic.cs
   To: Documents\NinjaTrader 8\bin\Custom\Indicators\
   ```

2. **Compile:**
   - Press F3 (NinjaScript Editor)
   - Press F5 (Compile)
   - Look for "Compiled successfully"

### Step 2: Apply Diagnostic to Your Chart

1. **On the chart that's giving you problems**, right-click → **Indicators**
2. Find **ChartDiagnostic** in the list
3. Click **Add** (or double-click it)
4. Click **OK**

### Step 3: Check the Output

Press **F5** to see the Output window.

#### If Diagnostic Works, You'll See:
```
================================================
ChartDiagnostic: SetDefaults completed
================================================
ChartDiagnostic: Configure state reached
ChartDiagnostic: DataLoaded state
  Instrument: ES DEC25
  BarsPeriod Type: Minute
  Bars Count: 100
================================================
ChartDiagnostic: OnBarUpdate() called!
  CurrentBar: 0
  Time[0]: 12/04/2024 09:30:00
  Close[0]: 4825.5
  SUCCESS: Chart data is accessible!
================================================
```

✅ **If you see this** - Your chart has data! The issue is strategy-specific. Skip to "Solution A" below.

#### If Diagnostic Also Fails:
```
ChartDiagnostic: SetDefaults completed
ChartDiagnostic: Terminated
CurrentBar at termination: -1
```

❌ **If you see this** - Your chart has no loadable data. Follow "Solution B" below.

---

## Solution A: Chart Has Data (Indicator Works, Strategy Doesn't)

If the ChartDiagnostic indicator succeeds, the issue is with strategy-specific requirements.

### Fix 1: Check Calculate Mode

Some data series don't support `Calculate.OnEachTick` for strategies.

1. Open the strategy in NinjaScript Editor
2. In `OnStateChange()`, under `State.SetDefaults`, find:
   ```csharp
   Calculate = Calculate.OnEachTick;
   ```
3. Change it to:
   ```csharp
   Calculate = Calculate.OnBarClose;
   ```
4. Recompile (F5) and try again

### Fix 2: Remove Trading-Specific Settings

The strategy might have settings that require a brokerage connection:

1. In DataFeederStrategy.cs, find these lines and comment them out:
   ```csharp
   // StartBehavior = StartBehavior.WaitUntilFlat;
   // IsExitOnSessionCloseStrategy = true;
   // ExitOnSessionCloseSeconds = 30;
   ```
2. Recompile and try again

### Fix 3: Use a Different Chart Type

Try creating a chart with different settings:
- Type: **Second** (instead of Minute)
- Value: **30**
- Days to load: **1**

---

## Solution B: Chart Has No Loadable Data

If even the indicator fails, the chart truly has no bars loaded.

### Fix 1: Check Data Series Settings

1. **Right-click the chart** → **Data Series**
2. Look at the settings:
   - **Type**: Should be Minute, Second, Tick, or Volume (NOT Day, Line, etc.)
   - **Value**: Should be greater than 0
   - **Days to load**: Should be 1 or more (NOT 0)
3. If any are wrong, fix them and click **OK**

### Fix 2: Reload Historical Data

1. **Right-click chart** → **Reload All Historical Data**
2. Wait a few seconds for data to load
3. Verify you see bars on the chart
4. Try the diagnostic indicator again

### Fix 3: Check Instrument Validity

The instrument "ES DEC25" might have issues.

**Try a different instrument:**
- `NQ 03-25` (E-mini Nasdaq)
- `AAPL` (Apple stock)
- `MSFT` (Microsoft stock)
- `EUR/USD` (Forex, if available)

**Create a new chart:**
1. File → New → Chart (Ctrl+N)
2. Instrument: `AAPL`
3. Type: `Minute`
4. Value: `1`
5. Days to load: `2`
6. Click OK
7. Apply ChartDiagnostic indicator

### Fix 4: Use Playback Connection

If you're having data connection issues, use simulated data:

1. **Disconnect** from any current connections
2. Click **Connections → Playback Connection**
3. Create new chart: `ES 03-25`, `1 Minute`, `2 Days`
4. Open **Tools → Playback Controller**
5. Set a date (click calendar icon)
6. Click **Play** button
7. Apply ChartDiagnostic indicator

---

## Solution C: Chart Type Is Incompatible

Some chart types don't support strategies at all.

### Incompatible Chart Types (Won't Work):
- ❌ Line charts
- ❌ Point & Figure
- ❌ Kagi, Renko (unless specifically configured)
- ❌ Market Depth
- ❌ Volume Profile
- ❌ Order Flow+

### Compatible Chart Types (Will Work):
- ✅ Minute bars
- ✅ Second bars
- ✅ Tick bars
- ✅ Volume bars
- ✅ Day bars

**How to check:**
1. Look at the top of your chart
2. Find the bar type indicator
3. If it says anything other than Minute/Second/Tick/Volume, create a new chart

**Create a compatible chart:**
1. File → New → Chart
2. Choose **Minute** bars
3. Value: `1`
4. Days: `2`

---

## Solution D: Using a Fresh Default Chart

Sometimes the best solution is to start completely fresh:

### Create a Guaranteed-Working Chart:

1. **Close all charts** in NinjaTrader
2. Click **File → New → Chart** (Ctrl+N)
3. Use these EXACT settings:
   - **Instrument**: `ES 03-25`
   - **Chart Type**: `Minute`
   - **Value**: `1`
   - **Days to load**: `2`
   - **Data connection**: Kinetick End-of-Day (or Playback)
4. Click **OK**
5. **Wait for bars to appear** on the chart
6. Apply **ChartDiagnostic** indicator
7. Check Output (F5)

---

## Checklist for Strategy Success

Before applying any strategy, verify:

- [ ] **Indicator works first** (ChartDiagnostic shows success)
- [ ] **Chart shows bars** visually (not empty)
- [ ] **Chart type is Minute/Second/Tick/Volume** (check top of chart)
- [ ] **Data Series → Days to load** is 1 or more (not 0)
- [ ] **Calculate mode** is OnBarClose (not OnEachTick) for testing
- [ ] **Connection** is established (green indicator)
- [ ] **Instrument** is valid and not expired

---

## What to Do Next

1. **Install and run ChartDiagnostic** indicator on your chart
2. **Copy the full output** from the Output window (F5)
3. **Paste it** and I'll tell you exactly what's wrong

The diagnostic output will show me:
- Whether Configure state is reached
- What the BarsPeriod settings are
- How many bars are actually loaded
- Whether OnBarUpdate() ever fires
- The exact point where things fail

This will pinpoint the exact issue so we can fix it!

---

## Common Causes & Quick Fixes

| Problem | Solution |
|---------|----------|
| Days to load = 0 | Right-click chart → Data Series → Set Days to load = 2 |
| Calculate.OnEachTick incompatible | Change to Calculate.OnBarClose in strategy code |
| Line chart type | Create new chart with Minute bars |
| Expired futures contract | Use current contract (ES 03-25 instead of ES 06-24) |
| No data connection | Connect to data provider or use Playback Connection |
| Chart just created | Wait 10-20 seconds for data to load, then reload |

---

## Still Not Working?

If ChartDiagnostic also goes SetDefaults → Terminated immediately, try:

1. **Restart NinjaTrader** completely
2. **Create a brand new workspace**: File → Workspaces → New Workspace
3. **Create a fresh chart** with ES 03-25, 1 Minute
4. **Try ChartDiagnostic again**

Share the ChartDiagnostic output and I'll provide the next fix!
