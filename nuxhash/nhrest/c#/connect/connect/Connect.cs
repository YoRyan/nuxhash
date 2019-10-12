using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace connect
{
    class Connect
    {
        static void Main(string[] args)
        {
            Console.WriteLine("running HashPowerOrder");
            new Hpo();
            Console.WriteLine("\n\nrunning Exchange");
            new Exch();
            Console.ReadLine();
        }
    }

    public class ServerTime
    {
        public string serverTime { get; set; }
    }
    public class Pool
    {
        public string id { get; set; }
    }
    public class Order
    {
        public string id { get; set; }
    }
    public class OrderBooks
    {
        public List<double[]> sell { get; set; }
        public List<double[]> buy { get; set; }
    }
}
