#!/bin/bash
# Configuration
ORG="---"
KEY="---"
SEC="---"
#API="https://api2.nicehash.com" #prod env
API="https://api-test.nicehash.com" # test env

# Command
NHCLIENT="python nicehash.py -b $API -o $ORG -k $KEY -s $SEC"

# Run method
eval "$NHCLIENT -m GET -p '/main/api/v2/accounting/accounts'"; # -b '{json}'
