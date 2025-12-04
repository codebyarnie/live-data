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
            if (State == State.SetDefaults)
            {
                Description = @"Simple test strategy to verify NinjaTrader is working";
                Name = "SimpleTestStrategy";
                Calculate = Calculate.OnBarClose;
                BarsRequiredToTrade = 1;

                Print("========================================");
                Print("SimpleTestStrategy: LOADED SUCCESSFULLY");
                Print("========================================");
            }
            else if (State == State.DataLoaded)
            {
                Print("SimpleTestStrategy: Data loaded, ready to start");
            }
            else if (State == State.Realtime)
            {
                Print("========================================");
                Print("SimpleTestStrategy: NOW RUNNING IN REAL-TIME");
                Print($"Instrument: {Instrument.FullName}");
                Print("You should see bar updates below...");
                Print("========================================");
            }
            else if (State == State.Terminated)
            {
                Print("========================================");
                Print("SimpleTestStrategy: STOPPED");
                Print($"Total bars processed: {barCounter}");
                Print("========================================");
            }
        }

        protected override void OnBarUpdate()
        {
            barCounter++;

            // Print first 5 bars
            if (barCounter <= 5)
            {
                Print($"Bar #{barCounter}: Time={Time[0]:MM/dd HH:mm:ss}, Close=${Close[0]}, Volume={Volume[0]}");
            }

            // Then print every 10th bar
            if (barCounter > 5 && barCounter % 10 == 0)
            {
                Print($"Bar #{barCounter}: Still running... Close=${Close[0]}");
            }

            // Print when in real-time mode
            if (State == State.Realtime && barCounter <= 3)
            {
                Print($"  → REAL-TIME BAR #{barCounter}");
            }
        }
    }
}
