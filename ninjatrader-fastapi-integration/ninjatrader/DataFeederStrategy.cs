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

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Sends market data to FastAPI backend";
                Name = "DataFeederStrategy";
                Calculate = Calculate.OnEachTick;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 1;
                IsInstantiatedOnEachOptimizationIteration = true;
            }
            else if (State == State.Configure)
            {
                // Initialize HTTP client
                httpClient = new HttpClient();
                httpClient.Timeout = TimeSpan.FromSeconds(5);
                lastUpdateTime = DateTime.MinValue;
            }
            else if (State == State.Terminated)
            {
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
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // Check if enough time has passed since last update
            if ((DateTime.Now - lastUpdateTime).TotalSeconds < updateInterval)
                return;

            lastUpdateTime = DateTime.Now;

            // Send data asynchronously without blocking the strategy
            Task.Run(async () => await SendDataToAPI());
        }

        private async Task SendDataToAPI()
        {
            // Use semaphore to prevent multiple simultaneous requests
            if (!await httpSemaphore.WaitAsync(0))
                return;

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

                if (response.IsSuccessStatusCode)
                {
                    Print($"Data sent successfully for {Instrument.FullName} at {Time[0]}");
                }
                else
                {
                    Print($"Failed to send data. Status: {response.StatusCode}");
                }
            }
            catch (Exception ex)
            {
                Print($"Error sending data to API: {ex.Message}");
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
