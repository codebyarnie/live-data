#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// Use an INDICATOR instead of a strategy to diagnose chart data
// Indicators are more forgiving and will show us what's available

namespace NinjaTrader.NinjaScript.Indicators
{
    public class ChartDiagnostic : Indicator
    {
        private bool diagnosticRun = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Diagnostic tool to check chart data availability";
                Name = "ChartDiagnostic";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = true;
                DrawOnPricePanel = true;
                PaintPriceMarkers = false;
                ScaleJustification = NinjaTrader.Gui.Chart.ScaleJustification.Right;
                IsSuspendedWhileInactive = false;

                Print("================================================");
                Print("ChartDiagnostic: SetDefaults completed");
                Print("================================================");
            }
            else if (State == State.Configure)
            {
                Print("ChartDiagnostic: Configure state reached");
            }
            else if (State == State.DataLoaded)
            {
                Print("================================================");
                Print("ChartDiagnostic: DataLoaded state");
                Print($"  Instrument: {(Instrument != null ? Instrument.FullName : "NULL")}");
                Print($"  Master Instrument: {(Instrument?.MasterInstrument != null ? Instrument.MasterInstrument.Name : "NULL")}");
                Print($"  BarsPeriod Type: {(BarsPeriod != null ? BarsPeriod.BarsPeriodType.ToString() : "NULL")}");
                Print($"  BarsPeriod Value: {(BarsPeriod != null ? BarsPeriod.Value.ToString() : "NULL")}");
                Print($"  BarsArray Length: {(BarsArray != null ? BarsArray.Length.ToString() : "NULL")}");
                if (BarsArray != null && BarsArray.Length > 0)
                {
                    Print($"  Bars Count: {(BarsArray[0] != null ? BarsArray[0].Count.ToString() : "NULL")}");
                    Print($"  Bars IsValidDataPoint: {(BarsArray[0] != null ? BarsArray[0].IsValidDataPoint.ToString() : "NULL")}");
                }
                Print($"  CurrentBar: {CurrentBar}");
                Print($"  Calculate: {Calculate}");
                Print("================================================");
            }
            else if (State == State.Historical)
            {
                Print("ChartDiagnostic: Historical state - processing historical data");
            }
            else if (State == State.Transition)
            {
                Print("ChartDiagnostic: Transition state - moving to real-time");
            }
            else if (State == State.Realtime)
            {
                Print("================================================");
                Print("ChartDiagnostic: Realtime state reached!");
                Print("  Chart has data and is working properly");
                Print("================================================");
            }
            else if (State == State.Terminated)
            {
                Print("================================================");
                Print("ChartDiagnostic: Terminated");
                Print($"  CurrentBar at termination: {CurrentBar}");
                Print($"  Diagnostic run: {diagnosticRun}");
                Print("================================================");
            }
        }

        protected override void OnBarUpdate()
        {
            if (!diagnosticRun)
            {
                diagnosticRun = true;
                Print("================================================");
                Print("ChartDiagnostic: OnBarUpdate() called!");
                Print($"  CurrentBar: {CurrentBar}");
                Print($"  Count: {Count}");
                Print($"  State: {State}");

                if (CurrentBar >= 0)
                {
                    Print($"  Time[0]: {Time[0]}");
                    Print($"  Close[0]: {Close[0]}");
                    Print($"  Volume[0]: {Volume[0]}");
                    Print($"  High[0]: {High[0]}");
                    Print($"  Low[0]: {Low[0]}");
                }

                Print("  SUCCESS: Chart data is accessible!");
                Print("  You can now use strategies on this chart.");
                Print("================================================");
            }

            // Draw text on chart to show it's working
            if (CurrentBar % 10 == 0 && State == State.Realtime)
            {
                Draw.TextFixed(this, "diagnostic", $"Chart OK - Bar: {CurrentBar}", TextPosition.TopLeft,
                    Brushes.LimeGreen, new Gui.Tools.SimpleFont("Arial", 12), Brushes.Transparent, Brushes.Transparent, 0);
            }
        }
    }
}
