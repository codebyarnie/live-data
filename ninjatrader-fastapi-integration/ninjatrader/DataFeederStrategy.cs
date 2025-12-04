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
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using System.Net.Http;
using System.Threading;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class DataFeederStrategy : Strategy
    {
        private HttpClient httpClient;
        private string apiEndpoint = "http://localhost:8000/data";
        private int updateInterval = 1; // seconds between updates
        private DateTime lastUpdateTime;
        private SemaphoreSlim httpSemaphore = new SemaphoreSlim(1, 1);
        private int barCount = 0;
        private int dataSentCount = 0;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Sends market data to FastAPI backend";
                Name = "DataFeederStrategy";

                // Use OnBarClose instead of OnEachTick for better compatibility
                // OnEachTick can be changed later once you verify it works
                Calculate = Calculate.OnBarClose;

                // Minimal strategy settings for data-only usage (no trading)
                BarsRequiredToTrade = 0;
                IsInstantiatedOnEachOptimizationIteration = true;

                // These are left as defaults but not required for data feeding
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;

                // Removed these to avoid requiring brokerage connection:
                // StartBehavior = StartBehavior.WaitUntilFlat;
                // IsExitOnSessionCloseStrategy = true;
                // ExitOnSessionCloseSeconds = 30;

                // Print to confirm strategy is loaded
                Print("========================================");
                Print("DataFeederStrategy: SetDefaults completed");
                Print("  Using Calculate.OnBarClose for compatibility");
                Print("  (Change to OnEachTick in code if you need tick data)");
                Print("========================================");
            }
            else if (State == State.Configure)
            {
                Print("DataFeederStrategy: Configuring...");
                // Initialize HTTP client
                httpClient = new HttpClient();
                httpClient.Timeout = TimeSpan.FromSeconds(5);
                lastUpdateTime = DateTime.MinValue;
                Print("DataFeederStrategy: Configuration completed");
            }
            else if (State == State.DataLoaded)
            {
                Print("=========================================");
                Print("DataFeederStrategy: STARTED");
                Print($"Instrument: {Instrument.FullName}");
                Print($"API Endpoint: {apiEndpoint}");
                Print($"Update Interval: {updateInterval} seconds");
                Print("Waiting for bars to load...");
                Print("=========================================");
            }
            else if (State == State.Historical)
            {
                Print("DataFeederStrategy: Processing historical data...");
            }
            else if (State == State.Transition)
            {
                Print("DataFeederStrategy: Transitioning to real-time...");
            }
            else if (State == State.Realtime)
            {
                Print("=========================================");
                Print("DataFeederStrategy: NOW IN REAL-TIME MODE");
                Print("Data will be sent to FastAPI backend");
                Print("=========================================");
            }
            else if (State == State.Terminated)
            {
                Print("=========================================");
                Print($"DataFeederStrategy: TERMINATED");
                Print($"Total bars processed: {barCount}");
                Print($"Total data sent: {dataSentCount}");
                Print("=========================================");

                // Clean up HTTP client
                if (httpClient != null)
                {
                    httpClient.Dispose();
                    httpClient = null;
                }
                if (httpSemaphore != null)
                {
                    httpSemaphore.Dispose();
                    httpSemaphore = null;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            // Count bars for debugging
            barCount++;

            // Print first few bars to confirm strategy is running
            if (barCount <= 3)
            {
                Print($"Bar {barCount}: CurrentBar={CurrentBar}, Time={Time[0]}, Close={Close[0]}, State={State}");
            }

            // Only send data in real-time mode (skip historical processing)
            if (State != State.Realtime)
            {
                if (barCount <= 3)
                    Print($"  → Skipping (not in Realtime yet)");
                return;
            }

            // Check if enough time has passed since last update
            if ((DateTime.Now - lastUpdateTime).TotalSeconds < updateInterval)
                return;

            lastUpdateTime = DateTime.Now;

            // Print every 10th data send attempt for debugging
            if (dataSentCount % 10 == 0)
            {
                Print($"Attempting to send data #{dataSentCount + 1}...");
            }

            // Send data asynchronously without blocking the strategy
            Task.Run(async () => await SendDataToAPI());
        }

        private async Task SendDataToAPI()
        {
            // Use semaphore to prevent multiple simultaneous requests
            if (!await httpSemaphore.WaitAsync(0))
            {
                Print("Previous request still in progress, skipping...");
                return;
            }

            try
            {
                // Prepare the data payload
                var data = new
                {
                    symbol = Instrument.FullName,
                    timestamp = Time[0].ToString("yyyy-MM-ddTHH:mm:ss"),
                    price = Close[0],
                    volume = Volume[0],
                    bid = GetCurrentBid(),
                    ask = GetCurrentAsk(),
                    high = High[0],
                    low = Low[0],
                    open = Open[0],
                    close = Close[0]
                };

                // Convert to JSON
                string jsonContent = Newtonsoft.Json.JsonConvert.SerializeObject(data);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                // Send POST request
                var response = await httpClient.PostAsync(apiEndpoint, content);

                dataSentCount++;

                if (response.IsSuccessStatusCode)
                {
                    if (dataSentCount <= 3 || dataSentCount % 10 == 0)
                    {
                        Print($"✓ Data #{dataSentCount} sent successfully: {Instrument.FullName} @ {Close[0]}");
                    }
                }
                else
                {
                    Print($"✗ Failed to send data #{dataSentCount}. HTTP Status: {response.StatusCode}");
                }
            }
            catch (HttpRequestException ex)
            {
                Print($"✗ HTTP Error: {ex.Message}");
                Print("  → Is the FastAPI server running on " + apiEndpoint + "?");
            }
            catch (TaskCanceledException ex)
            {
                Print($"✗ Request timeout: {ex.Message}");
            }
            catch (Exception ex)
            {
                Print($"✗ Error sending data to API: {ex.GetType().Name} - {ex.Message}");
            }
            finally
            {
                httpSemaphore.Release();
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "API Endpoint", Description = "FastAPI endpoint URL", Order = 1, GroupName = "Parameters")]
        public string ApiEndpoint
        {
            get { return apiEndpoint; }
            set { apiEndpoint = value; }
        }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Update Interval (seconds)", Description = "Seconds between data updates", Order = 2, GroupName = "Parameters")]
        public int UpdateInterval
        {
            get { return updateInterval; }
            set { updateInterval = Math.Max(1, value); }
        }
        #endregion
    }
}
