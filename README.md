# wheathersite
API rate limit test with Django

## Requirements

We are required to create a module that implements rate limiting to API requests.
The requirements are:

1. You should be able to configure the rate limit being enforced by the module.
2. The module should inform the API consumer about the current rate limit and the remaining number of available calls.
3. The module should respond with status code 429 (Too Many Requests) if a consumer reaches the limit of requests.

## Implementation

Django...
Decorator...
How it's implemented (cache, how the IP is determined, headers X-CURRENT-RATE-LIMIT and X-REMAINING-CALLS)
How it's used, default values.
Change rate
Improvements (rate for authenticated users, rates per roles... all can be done calculating different cache keys)

## How to install
Docker


## Tests
Automatic tests
Postman collection. Run postman collection


