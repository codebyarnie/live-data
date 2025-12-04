#region Using declarations
using System;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

// This is a MINIMAL test strategy to verify NinjaTrader is working
// Use this to confirm basic functionality before using DataFeederStrategy

namespace NinjaTrader.NinjaScript.Strategies
{
    public class SimpleTestStrategy : Strategy
    {
        private int barCounter = 0;

        protected override void OnStateChange()
        {
            Print($"[SimpleTestStrategy] OnStateChange called - State: {State}");

            if (State == State.SetDefaults)
            {
                Description = @"Simple test strategy to verify NinjaTrader is working";
                Name = "SimpleTestStrategy";
                Calculate = Calculate.OnBarClose;
                BarsRequiredToTrade = 0;  // Changed to 0 to process all bars
                IsInstantiatedOnEachOptimizationIteration = true;

                Print("========================================");
                Print("SimpleTestStrategy: LOADED SUCCESSFULLY");
                Print("========================================");
            }
            else if (State == State.Configure)
            {
                Print("SimpleTestStrategy: State.Configure - Configuring strategy");
            }
            else if (State == State.DataLoaded)
            {
                Print("========================================");
                Print("SimpleTestStrategy: State.DataLoaded");
                Print($"  Chart Instrument: {Instrument?.FullName ?? "NULL"}");
                Print($"  Bar Period: {BarsPeriod?.BarsPeriodType.ToString() ?? "NULL"}");
                Print($"  Current Bars: {CurrentBar}");
                Print("========================================");
            }
            else if (State == State.Historical)
            {
                Print("SimpleTestStrategy: State.Historical - Processing historical data");
            }
            else if (State == State.Transition)
            {
                Print("SimpleTestStrategy: State.Transition - Moving to real-time");
            }
            else if (State == State.Realtime)
            {
                Print("========================================");
                Print("SimpleTestStrategy: State.Realtime - NOW RUNNING IN REAL-TIME");
                Print($"Instrument: {Instrument.FullName}");
                Print("You should see bar updates below...");
                Print("========================================");
            }
            else if (State == State.Terminated)
            {
                Print("========================================");
                Print("SimpleTestStrategy: STOPPED");
                Print($"  Final State before termination: {State}");
                Print($"  Total bars processed: {barCounter}");
                Print($"  CurrentBar at termination: {CurrentBar}");
                if (Instrument != null)
                    Print($"  Instrument was: {Instrument.FullName}");
                else
                    Print("  ERROR: Instrument was NULL!");
                Print("========================================");
            }
        }

        protected override void OnBarUpdate()
        {
            barCounter++;

            // Print EVERY bar for debugging
            Print($"Bar #{barCounter}: CurrentBar={CurrentBar}, Time={Time[0]:MM/dd HH:mm:ss}, Close=${Close[0]:F2}, Volume={Volume[0]}, State={State}");

            // Additional info for first 3 bars
            if (barCounter <= 3)
            {
                Print($"  → Bar Index: {CurrentBar}, BarsArray Count: {BarsArray[0].Count}");
            }
        }
    }
}
