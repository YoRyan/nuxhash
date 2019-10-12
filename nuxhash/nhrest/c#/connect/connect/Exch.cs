using NLog;
using System;
using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace connect
{
    class Exch
    {
        private static NLog.Logger Logger = NLog.LogManager.GetCurrentClassLogger();

        private static string URL_ROOT   = "https://api-test.nicehash.com"; //use https://api2.nicehash.com for production
        private static string ORG_ID     = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
        private static string API_KEY    = "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj";
        private static string API_SECRET = "kkkkkkkk-llll-mmmm-nnnn-oooooooooooooooooooo-pppp-qqqq-rrrr-ssssssssssss";

        private static string CURRENCY_SELL = "TBTC"; //user BTC for production
        private static string CURRENCY_BUY  = "TLTC"; //use LTC for production

        public Exch()
        {
            var config = new NLog.Config.LoggingConfiguration();
            var logconsole = new NLog.Targets.ConsoleTarget("logconsole");
            config.AddRule(LogLevel.Info, LogLevel.Fatal, logconsole);
            NLog.LogManager.Configuration = config;

            Api api = new Api(URL_ROOT, ORG_ID, API_KEY, API_SECRET);

            //get server time
            string timeResponse = api.get("/api/v2/time");
            ServerTime serverTimeObject = Newtonsoft.Json.JsonConvert.DeserializeObject<ServerTime>(timeResponse);
            string time = serverTimeObject.serverTime;
            Logger.Info("server time: {}", time);

            //get algo settings
            string exchResponse = api.get("/exchange/api/v2/info/status");
            Console.WriteLine("[[["+exchResponse+"]]]");
            DataTable exchArray = Newtonsoft.Json.JsonConvert.DeserializeObject<DataTable>(exchResponse);

            DataRow mySettings = null;
            foreach (DataRow symbol in exchArray.Rows)
            {
                if (symbol["baseAsset"].Equals(CURRENCY_BUY))
                {
                    mySettings = symbol;
                }
            }
            Logger.Info("exchange settings: {}", mySettings["currency"]);

            //get balance
            string accountsResponse = api.get("/main/api/v2/accounting/accounts", true, time);
            DataTable accountsArray = Newtonsoft.Json.JsonConvert.DeserializeObject<DataTable>(accountsResponse);

            DataRow myBalace = null;
            foreach (DataRow account in accountsArray.Rows)
            {
                if (account["currency"].Equals(CURRENCY_SELL))
                {
                    myBalace = account;
                }
            }
            Logger.Info("balance: {} {}", myBalace["balance"], CURRENCY_SELL);

            //get order book
            string orderBookResponse = api.get("/exchange/api/v2/orderbook?market=" + CURRENCY_BUY + CURRENCY_SELL + "&limit=100", true, time);
            OrderBooks orderBooks = Newtonsoft.Json.JsonConvert.DeserializeObject<OrderBooks>(orderBookResponse);
            Logger.Info("cheapest offer price: {} supply: {}", orderBooks.sell[0][0], orderBooks.sell[0][1]);

            double qty = 0.1 * 2;
            string sQty = qty.ToString("0.00000000", System.Globalization.CultureInfo.InvariantCulture);
            string sPrice = orderBooks.sell[0][0].ToString("0.00000000", System.Globalization.CultureInfo.InvariantCulture);

            //buy with limit order
            string url = "/exchange/api/v2/order?market=" + CURRENCY_BUY + CURRENCY_SELL + "&side=buy&type=limit&quantity=" + sQty + "&price=" + sPrice;
            Logger.Info("order url: {}", url);
            string orderCreateResponse = api.post(url, null, time, true);
            Logger.Info("order create: {}", orderCreateResponse);
        }
    }

}
