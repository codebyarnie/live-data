#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Text;
using System.Threading.Tasks;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.Gui.Tools;
using System.Net.Http;
using System.Threading;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using System.Windows.Media;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class DataFeederIndicator : Indicator
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
            Print($"[DataFeederIndicator] State: {State}");

            if (State == State.SetDefaults)
            {
                Description = @"Sends market data to FastAPI backend (INDICATOR VERSION)";
                Name = "DataFeederIndicator";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = false;
                DrawOnPricePanel = true;
                PaintPriceMarkers = false;
                IsSuspendedWhileInactive = true;

                Print("========================================");
                Print("DataFeederIndicator: LOADED");
                Print("========================================");
            }
            else if (State == State.Configure)
            {
                Print("DataFeederIndicator: Configuring...");
                httpClient = new HttpClient();
                httpClient.Timeout = TimeSpan.FromSeconds(5);
                lastUpdateTime = DateTime.MinValue;
            }
            else if (State == State.DataLoaded)
            {
                Print("=========================================");
                Print("DataFeederIndicator: DATA LOADED ✓");
                Print($"  Instrument: {Instrument.FullName}");
                Print($"  API Endpoint: {apiEndpoint}");
                Print($"  Update Interval: {updateInterval} seconds");
                Print($"  Bars available: {BarsArray[0].Count}");
                Print("=========================================");
            }
            else if (State == State.Historical)
            {
                Print("DataFeederIndicator: Processing historical data...");
            }
            else if (State == State.Realtime)
            {
                Print("=========================================");
                Print("DataFeederIndicator: NOW LIVE! ✓✓✓");
                Print("  Sending data to FastAPI backend...");
                Print("=========================================");
            }
            else if (State == State.Terminated)
            {
                Print("=========================================");
                Print($"DataFeederIndicator: STOPPED");
                Print($"  Total bars: {barCount}");
                Print($"  Data sent: {dataSentCount}");
                Print("=========================================");

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
            barCount++;

            // Print first few bars to confirm it's working
            if (barCount <= 3)
            {
                Print($"Bar #{barCount}: CurrentBar={CurrentBar}, Time={Time[0]:MM/dd HH:mm:ss}, Close=${Close[0]:F2}, State={State}");
            }

            // Only send data in real-time mode
            if (State != State.Realtime)
            {
                if (barCount <= 3)
                    Print($"  → Skipping (State={State})");
                return;
            }

            // Check if enough time has passed
            if ((DateTime.Now - lastUpdateTime).TotalSeconds < updateInterval)
                return;

            lastUpdateTime = DateTime.Now;

            // Log every 10th send for debugging
            if (dataSentCount % 10 == 0)
            {
                Print($"Sending data #{dataSentCount + 1}...");
            }

            // Send data asynchronously
            Task.Run(async () => await SendDataToAPI());
        }

        private async Task SendDataToAPI()
        {
            if (!await httpSemaphore.WaitAsync(0))
            {
                Print("Previous request in progress, skipping...");
                return;
            }

            try
            {
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

                string jsonContent = Newtonsoft.Json.JsonConvert.SerializeObject(data);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                var response = await httpClient.PostAsync(apiEndpoint, content);

                dataSentCount++;

                if (response.IsSuccessStatusCode)
                {
                    if (dataSentCount <= 3 || dataSentCount % 10 == 0)
                    {
                        Print($"✓ Data #{dataSentCount} sent: {Instrument.FullName} @ {Close[0]:F2}");
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
                Print($"  → Is FastAPI running at {apiEndpoint}?");
            }
            catch (TaskCanceledException ex)
            {
                Print($"✗ Request timeout: {ex.Message}");
            }
            catch (Exception ex)
            {
                Print($"✗ Error: {ex.GetType().Name} - {ex.Message}");
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
        [Display(Name = "Update Interval (seconds)", Description = "Seconds between updates", Order = 2, GroupName = "Parameters")]
        public int UpdateInterval
        {
            get { return updateInterval; }
            set { updateInterval = Math.Max(1, value); }
        }
        #endregion
    }
}