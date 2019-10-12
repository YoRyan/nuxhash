import nicehash

# For testing purposes use api-test.nicehash.com. Register here: https://test.nicehash.com


# When ready, uncomment line bellow, to run your script on production environment
# host = 'https://api2.nicehash.com'


# How to create key, secret and where to get organisation id please check:


# Production - https://www.nicehash.com
# host = 'https://api2.nicehash.com'
# organisation_id = 'Enter your organisation id'
# key = 'Enter your api key'
# secret = 'Enter your secret for api key'


# # Test - https://test.nicehash.com
# host = 'https://api-test.nicehash.com'
# organisation_id = '286fcf65-d44e-4cdf-81f2-4790c0cbed04'
# key = '6b957253-bcb9-4b83-b431-4f28ab783a6f'
# secret = 'ac09da0c-0b41-49ba-be6f-4698f9c184a67c6a834f-5bfe-5389-ba6f-d9ada9a86c03'

############################################
# PUBLIC FUNCTIONS

# Create public api object
public_api = nicehash.public_api(host, True)

# Get all algorithms
algorithms = public_api.get_algorithms()
print(algorithms)

# Get all markets
markets = public_api.get_markets()
print(markets)

# Get all curencies
currencies = public_api.get_curencies()
print(currencies)

# Get current global stats
global_stats_current = public_api.get_current_global_stats()
print(global_stats_current)

# Get global stats for 24h
global_stats_24h = public_api.get_global_stats_24()
print(global_stats_24h)

# Get orders for certain algorithm
global_active_orders = public_api.get_active_orders()
print(global_active_orders)

# Buy info
buy_info = public_api.buy_info()
print(buy_info)

# Get multialgo info
multialgo_info = public_api.get_multialgo_info()
print(multialgo_info)


############################################
# PRIVATE FUNCTIONS

# Create private api object
private_api = nicehash.private_api(host, organisation_id, key, secret, True)

# Get balance for all currencies
my_accounts = private_api.get_accounts()
print(my_accounts)

# Get balance for BTC address
my_btc_account = private_api.get_accounts_for_currency(currencies['currencies'][0]['currency'])
print(my_btc_account)

# Get my active hashpower orders
my_top_active_x16r_eu_orders = private_api.get_my_active_orders('X16R', 'EU', 10)
print(my_top_active_x16r_eu_orders)

# Create pool
new_pool = private_api.create_pool('My best pool', 'X16R', 'the.best.pool.com', 3333, 'mybestcoinaddress', 'x')
print(new_pool)

# Get pools
pools_on_fist_page = private_api.get_my_pools(0, 10)
print(pools_on_fist_page)

# Create hashpower order
new_order = private_api.create_hashpower_order('EU', 'STANDARD', 'X16R', 0.123, 0, 0.005, pools_on_fist_page['list'][0]['id'], algorithms)
print(new_order)

# Refill hashpower order
refilled_order = private_api.refill_hashpower_order(new_order['id'], 0.005)
print(refilled_order)

# Order hashpower set price
set_price_order = private_api.set_price_hashpower_order(new_order['id'], 0.234, 'X16R', algorithms)
print(set_price_order)

# Order hashpower set limit
set_limit_order = private_api.set_limit_hashpower_order(new_order['id'], 2.12, 'X16R', algorithms)
print(set_limit_order)

# Order hashpower set price and imit
set_limit_order = private_api.set_price_and_limit_hashpower_order(new_order['id'], 0.235, 1.2, 'X16R', algorithms)
print(set_limit_order)

# Remove hashpower order
delete_hp_order = private_api.cancel_hashpower_order(new_order['id'])
print(delete_hp_order)

# Delete pool
delete_pool_result = private_api.delete_pool(new_pool['id'])
print(delete_pool_result)


############################################
# EXCHANGE

# Get exchange market info
exchange_info = public_api.get_exchange_markets_info()
print(exchange_info)

# Get trades for first market
trades = public_api.get_exchange_trades(exchange_info['symbols'][0]['symbol'])
print (trades)

# Get candlesticks
candlesticks = public_api.get_candlesticks(exchange_info['symbols'][0]['symbol'], 1561896404, 1567080464, 60)
print (candlesticks)

# Get exchange orderbook
exchange_orderbook = public_api.get_exchange_orderbook(exchange_info['symbols'][0]['symbol'], 10)
print (exchange_orderbook)

# Get my exchange orders
my_exchange_orders = private_api.get_my_exchange_orders(exchange_info['symbols'][0]['symbol'])
print (my_exchange_orders)

# Get my exchnage trades
my_exchange_trades = private_api.get_my_exchange_trades(exchange_info['symbols'][0]['symbol'])
print (my_exchange_trades)

# Create buy limit exchange order
new_sell_limit_order = private_api.create_exchange_limit_order(exchange_info['symbols'][0]['symbol'], 'sell', 10, 0.1)
print (new_sell_limit_order)

# Create sell limit exchange order
new_buy_limit_order = private_api.create_exchange_limit_order(exchange_info['symbols'][0]['symbol'], 'buy', 0.1, 0.1)
print (new_buy_limit_order)

# Create sell market order
new_sell_market_order = private_api.create_exchange_sell_market_order(exchange_info['symbols'][0]['symbol'], 0.1)
print(new_sell_market_order)

# Create buy market order
new_buy_market_order = private_api.create_exchange_buy_market_order(exchange_info['symbols'][0]['symbol'], 0.1)
print(new_buy_market_order)

# Cancel exchange order
cancelled_order = private_api.cancel_exchange_order(exchange_info['symbols'][0]['symbol'], my_exchange_orders[0]['orderId'])
print(cancelled_order)
