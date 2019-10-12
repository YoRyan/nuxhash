import com.google.gson.*;
import com.nicehash.connect.Api;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import java.util.UUID;

/**
 * hash power order example
 */
public class Hpo
{
	private Log log = LogFactory.getLog(Hpo.class);

	private static final String URL_ROOT   = "https://api-test.nicehash.com/"; //use https://api2.nicehash.com for production
	private static final String ORG_ID     = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"; //get it here: https://test.nicehash.com/my/settings/keys or https://new.nicehash.com/my/settings/keys
	private static final String API_KEY    = "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj";
	private static final String API_SECRET = "kkkkkkkk-llll-mmmm-nnnn-oooooooooooooooooooo-pppp-qqqq-rrrr-ssssssssssss";

	private static final String ALGORITHM = "X16R"; //algo of your order
	private static final String CURRENCY = "TBTC"; //user BTC for production

    public static void main( String[] args ) {
		new Hpo();
    }

	private Hpo() {
	    Api api = new Api(URL_ROOT, ORG_ID, API_KEY, API_SECRET);

	    //get server time
	    String timeResponse = api.get("api/v2/time");
		JsonObject timeObject = new Gson().fromJson(timeResponse, JsonObject.class);
		String time = timeObject.get("serverTime").getAsString();
	    log.info("server time: " + time);

	    //get algo settings
		String algosResponse = api.get("main/api/v2/mining/algorithms");
		JsonObject algoObject = new Gson().fromJson(algosResponse, JsonObject.class);
		//log.info("algorithms: " + algoObject.toString());

		final JsonObject[] settings = new JsonObject[1];
		algoObject.get("miningAlgorithms").getAsJsonArray().forEach(acc-> {
			JsonObject a = acc.getAsJsonObject();
			if (a.get("algorithm").getAsString().equals(ALGORITHM)) {
				settings[0] = a;
			}
		});

		JsonObject mySettings = settings[0];
		log.info("algo settings: " + mySettings);

	    //get balance
		String activityResponse = api.get("main/api/v2/accounting/accounts", true, time);
		JsonArray accountsArray = new Gson().fromJson(activityResponse, JsonArray.class);
		log.info("accounts: " + accountsArray.toString());

		final double[] balance = new double[1];
		accountsArray.forEach(acc-> {
			JsonObject a = acc.getAsJsonObject();
			if (a.get("currency").getAsString().equals(CURRENCY)) {
				balance[0] = a.get("balance").getAsDouble();
			}
		});

		double avaliableBalance = balance[0];
		log.info("balance: " + avaliableBalance + CURRENCY);

		//create new pool
		JsonObject pool = new JsonObject();
		pool.addProperty("algorithm", ALGORITHM);
		pool.addProperty("name", "my pool "+ UUID.randomUUID().toString());
		pool.addProperty("username", "pool_username"); //your pool username
		pool.addProperty("password", "x"); //your pool password
		pool.addProperty("stratumHostname", "pool.host.name"); //pool hostname
		pool.addProperty("stratumPort", "3456"); //pool port

		//log.info("new pool: " + pool.toString());
		String newPoolResponse = api.post("main/api/v2/pool", pool.toString(), time, false);
		//log.info("new pool response: " + newPoolResponse);
		JsonObject newPoolResponseObject = new Gson().fromJson(newPoolResponse, JsonObject.class);
		//log.info("new pool response object: " + newPoolResponseObject);

		String myPoolId = newPoolResponseObject.get("id").getAsString();
		log.info("new pool id: " + myPoolId);

		//create new order
		JsonObject order = new JsonObject();
		order.addProperty("algorithm", ALGORITHM);
		order.addProperty("amount", mySettings.get("minimalOrderAmount").getAsString());
		order.addProperty("displayMarketFactor", mySettings.get("displayMarketFactor").getAsString());
		order.addProperty("limit", mySettings.get("minSpeedLimit").getAsString()); // GH [minSpeedLimit-maxSpeedLimit] || 0 - unlimited speed
		order.addProperty("market", "EU"); // EU/USA
		order.addProperty("marketFactor", mySettings.get("marketFactor").getAsString());
		order.addProperty("poolId", myPoolId);
		order.addProperty("price", "0.0010"); //per BTC/GH/day
		order.addProperty("type", "STANDARD");

		//log.info("new order: " + order.toString());
		String newOrderResponse = api.post("main/api/v2/hashpower/order", order.toString(), time, true);
		//log.info("new order response: " + newOrderResponse);
		JsonObject newOrderResponseObject = new Gson().fromJson(newOrderResponse, JsonObject.class);
		//log.info("new order response object: " + newOrderResponseObject);
		log.info("new order response object: " + newOrderResponseObject);

		String myOrderId = newOrderResponseObject.get("id").getAsString();
		log.info("new order id: " + myOrderId);

		//update price and limit
		JsonObject updateOrder = new JsonObject();
		updateOrder.addProperty("displayMarketFactor", mySettings.get("displayMarketFactor").getAsString());
		updateOrder.addProperty("limit", "0.11"); // GH [minSpeedLimit-maxSpeedLimit] || 0 - unlimited speed
		updateOrder.addProperty("marketFactor", mySettings.get("marketFactor").getAsString());
		updateOrder.addProperty("price", "0.00123"); //per BTC/GH/day

		//log.info("update order: " + updateOrder.toString());
		String updateOrderResponse = api.post("main/api/v2/hashpower/order/"+myOrderId+"/updatePriceAndLimit", updateOrder.toString(), time, true);
		//log.info("update order response: " + updateOrderResponse);
		JsonObject updateOrderResponseObject = new Gson().fromJson(updateOrderResponse, JsonObject.class);
		log.info("update order response object: " + updateOrderResponseObject);

		//delete order
		String deleteOrderResponse = api.delete("main/api/v2/hashpower/order/"+myOrderId, time, true);
		//log.info("delete order response: " + deleteOrderResponse);
		JsonObject deleteOrderResponseObject = new Gson().fromJson(deleteOrderResponse, JsonObject.class);
		log.info("delete order response object: " + deleteOrderResponseObject);

		//delete pool
		String deletePoolResponse = api.delete("main/api/v2/pool/"+myPoolId, time, false);
		//log.info("delete pool response: " + deletePoolResponse);
		JsonObject deletePoolResponseObject = new Gson().fromJson(deletePoolResponse, JsonObject.class);
		log.info("delete pool response object: " + deletePoolResponseObject);
    }
}
