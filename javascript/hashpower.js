import config from './config'
import Api from './api'

var log = function () {
	return console.log(...arguments);
}

var algo, pool, order;

const api = new Api(config);

// get server time - required
api.getTime()
	.then(() => {
		log('server time', api.time)
		log('--')
	})

	// get algo settings
	.then(() => api.get('/main/api/v2/mining/algorithms'))
	.then(res => {
		algo = res.miningAlgorithms[0]; // SCRYPT
		log('algorithms', res);
		log('--')
	})

	// get balance
	// .then(() => api.get('/main/api/v2/accounting/accounts'))
	// .then(res => {
	// 	log('accounts', res);
	// })

	//// create new pool
	.then(() => {
		var body = {
			algorithm: 'SCRYPT',
			name: 'my pool',
			username: 'pool_username',
			password: 'x',
			stratumHostname: 'pool.host.name',
			stratumPort: '3456',
		};

		return api.post('/main/api/v2/pool',{body})
	})
	.then(res => {
		pool = res;
		log('new pool', res);
		log('--')
	})

	// create new order
	.then(() => {
		var body = {
			algorithm: 'SCRYPT',
			amount: "0.005",
			displayMarketFactor: algo.displayMarketFactor,
			limit: algo.minSpeedLimit,
			market: 'EU', // or USA
			marketFactor: algo.marketFactor,
			poolId: pool.id,
			price: '0.0010',
			type: 'STANDARD',
		};

		return api.post('/main/api/v2/hashpower/order',{body})
	})
	.then(res => {
		order = res;
		log('new order', res);
		log('--')
	})

	// update order price or limit
	.then(() => {
		var body = {
			displayMarketFactor: algo.displayMarketFactor,
			marketFactor: algo.marketFactor,
			limit: '0.11',
			price: '0.00123',
		};

		return api.post(`/main/api/v2/hashpower/order/${order.id}/updatePriceAndLimit`,{body})
	})
	.then(res => {
		log('updated order', res);
		log('--')
	})

	// cancel order
	.then(() => api.delete(`/main/api/v2/hashpower/order/${order.id}`))
	.then(res => {
		log('deleted order', res);
		log('--')
	})

	// delete pool
	.then(() => api.delete(`/main/api/v2/pool/${pool.id}`))
	.then(res => {
		log('deleted pool', res);
		log('--')
	})

	.catch(err => {
		if(err && err.response) log(err.response.request.method,err.response.request.uri.href);
		log('ERROR', err.error || err);
	})
