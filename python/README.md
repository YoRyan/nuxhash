# Nicehash python library and command line rest api

Dependacy
* requests

To install dependencies run following line your favorite shell console

    pip install requests
    
    
## Required data and where to get it
Following data is needed:
* api base url: 
    * https://api2.nicehash.com - Production environment
    * https://api-test.nicehash.com - Test environment
    
The documentation how to get organisation id, api key and api key secret is here:
https://github.com/nicehash/rest-clients-demo

## Library usage
Nicehash library is contained in file `nicehash.py`. Api is divided in two part: public and private.

Code snipplet for public api

    import nicehash
    
    host = 'https://api2.nicehash.com'
    
    public_api = nicehash.public_api(host)
    
    buy_info = public_api.buy_info()
    print(buy_info)
  
    
Code snipplet for private api
    
    import nicehash
    
    host = 'https://api2.nicehash.com'
    organisation_id = 'Enter your organisation id'
    key = 'Enter your api key'
    secret = 'Enter your secret for api key' 
    
    private_api = nicehash.private_api(host, organisation_id, key, secret)
    
    my_accounts = private_api.get_accounts()
    print(my_accounts)
    
    
Usage of other api calls are shown in `test_bot.py`


## Command line usage
`nicehash.py` can be used as commad line tools

To get help run:

    python nicehash.py -h
    
Result:
    
    Usage: nicehash.py [options]

    Options:
      -h, --help            show this help message and exit
      -b BASE, --base_url=BASE
                            Api base url
      -o ORG, --organization_id=ORG
                            Organization id
      -k KEY, --key=KEY     Api key
      -s SECRET, --secret=SECRET
                            Secret for api key
      -m METHOD, --method=METHOD
                            Method for request
      -p PATH, --path=PATH  Path for request
      -q PARAMS, --params=PARAMS
                            Parameters for request
      -d BODY, --body=BODY  Body for request


Example usage:

    python nicehash.py -b https://api2.nicehash.com -o ca5622bd-bc32-451b-90a4-e9ae1088bade -k 85512ceb-4f37-426e-9fb4-929af9134ed1 -s 11260065-37f9-4875-bbdd-52a59ce7775de2c0596c-5c87-4739-bb60-b3f547612aed -m GET -p /main/api/v2/accounting/accounts/
    
    
    

