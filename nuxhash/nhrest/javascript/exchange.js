import config from './config'
import Api from './api'

var log = function () {
	return console.log(...arguments);
}

var market, orderBook ,order;

const api = new Api(config);

// get server time - required
api.getTime()

	.then(() => {
		log('server time', api.time)
		log('--')
	})

	// get exchange settings
	.then(() => api.get('/exchange/api/v2/info/status'))
	.then(res => {
		market = res.symbols[0];
		log('exchange markets', res);
		log('--')
	})

	// get balance
	.then(() => api.get('/main/api/v2/accounting/accounts'))
	.then(res => {
		log('accounts', res);
		log('--')
	})

	// get orderbook
	.then(() => api.get('/exchange/api/v2/orderbook?aa=1',{query:{market: market.symbol}}))
	.then(res => {
		orderBook = res;
		log('order book for '+market.symbol, res);
		log('--')
	})

	// buy with limit order
	.then(() => {
		var query = {
			market: market.symbol,
			side: 'buy',
			type: 'limit',
			quantity: market.secMinAmount * 10,
			price: orderBook.sell[0][0],
		};

		return api.post('/exchange/api/v2/order',{query})
	})
	.then(res => {
		order = res;
		log('new order', res);
		log('--')
	})

	// cancel order
	.then(() => api.delete('/exchange/api/v2/order',{query:{market: market.symbol, orderId: order. orderId}}))
	.then(res => {
		orderBook = res;
		log('canceled order', res);
		log('--')
	})

	.catch(err => {
		if(err && err.response) log(err.response.request.method,err.response.request.uri.href);
		log('ERROR', err.error || err);
	})
