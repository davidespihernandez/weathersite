# Rate limit implementation
API rate limit test with Django

## 1. Requirements

We are required to create a module that implements rate limiting to API requests.
The requirements are:

1. You should be able to configure the rate limit being enforced by the module.
2. The module should inform the API consumer about the current rate limit and the remaining number of available calls.
3. The module should respond with status code 429 (Too Many Requests) if a consumer reaches the limit of requests.

### 1.1 Scope
We're going to implement a rate limiting system with these features:

- Limit the number of requests only for non-authenticated requests. Authenticated requests won't be limited.
- Limit the number of requests per minute.
- The specific allowed number of requests will be by default 60, but that can be changed in the settings. We can also specify the rate limit per specific endpoint.

## 2. Implementation

### 2.1 Architecture

We will use a simple Django site with two applications:

- `ratelimit`. This is the module containing the code that implements the rate limit. This app could be packaged and reused later in other projects. 
- `wheather`. This is an example app with two endpoints:
   * `/weather/limited`: Anonymous requests coming to this endpoint will have a rate limit of 60 requests per minute.
   * `/weather/unlimited`: Requests coming to this endpoint won't apply the rate limit. 

The interface defined by the `ratelimit` application is a decorator called `with_rate_limit`, that can be used to decorate the view functions and apply the rate limitation.

### 2.2 Implementation details
We use Django cache module to save the list (actually a queue) of request times done by each requesting IP. 
By default, Django uses a local-memory cache (per process, thread safe) which is convenient for a test environment. The cache backend can be changed easily to more performant and scalable cache backends like Memcached. 

If the request is authenticated, then no limitation is applied, and the request is processed normally.

This is what happens when an anonymous request is handled by the `with_rate_limit` decorator:

1. We retrieve the requesting IP using a library called `ipware` (https://github.com/un33k/django-ipware). 
   Under the hoods it uses some HTTP headers to retrieve the original IP requesting:

```
 'HTTP_X_FORWARDED_FOR', 
 'X_FORWARDED_FOR',  
 'HTTP_CLIENT_IP',
 'HTTP_X_REAL_IP',
 'HTTP_X_FORWARDED',
 'HTTP_X_CLUSTER_CLIENT_IP',
 'HTTP_FORWARDED_FOR',
 'HTTP_FORWARDED',
 'HTTP_VIA',
 'REMOTE_ADDR',
```

If the IP can't be retrieved, the request will be rejected with a 401.

The cache contents for each cache key is a queue that contains the request times for that cache key (IP address), ordered from newer (first item) to older (last item). New request times are inserted at the beginning of the list (queue).

2. We retrieve the cache contents for that IP as cache key. If there's no entry in the cache for that IP, an empty queue will be used.
3. All items in the queue older than 60 seconds (the default duration we use) are deleted. This is done looping from the end of the queue (where the older requests are).
4. The new request time (current time) is inserted at the beginning of the queue.
5. If after these steps we have more elements in the queue than the maximum number of requests per minute allowed, then a RateExceeded exception is raised. This is a Django REST framework API exception that will be translated into an HTTP 429 later.
6. The cache value is updated with the queue, setting an expiration time of 60 seconds. The cache will be cleaned automatically after that time, but every time a new request is added, the expiration time will be extended 60 seconds, and older request will be deleted from the queue.
7. If the request was anonymous and accepted (which means it was within the rate limits), then the request is performed and two headers are added to the response:
    * `X-CURRENT-RATE-LIMIT`. Contains the total number of requests per minute allowed (default 60)
    * `X-REMAINING-CALLS`. Contains how many calls can be performed until the rate limit is reached.
8. If the request was anonymous, and the rate limit was exceeded, then an HTTP 429 response is returned.
9. Authenticated requests are not limited, and won't contain the additional headers.

### 2.3 How to use the decorator

This is an example of a view applying the decorator, using the default number of 60 requests per minute:

```python
@api_view()
@with_rate_limit()
def limited(request):
    return Response({"message": f"Limited endpoint! {request.user}"})
```

That view will use an specific number of 10 requests per minute.

```python
@api_view()
@with_rate_limit(number_of_requests=10)
def limited(request):
    return Response({"message": f"Limited endpoint! {request.user}"})
```

### 2.4 How to change the rate

The default number of requests per minute is specified in a setting (`settings.py`).

```python
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
```

You can also set a specific number of requests per view, using the `number_of_requests` argument that the decorator receives. For example: 
```python
@with_rate_limit(number_of_requests=10)
```

### 2.5 Possible improvements
This code is just a test with basic features, but it contains the base to add easily some more advanced features:

* Apply rate limit to authenticated users. 
  In the case of authenticated users we can simply use the user id as the cache key, and also establish different default rates for authenticated and anonymous requests. 
  Limitations could also be applied per role, and in this case we should check several cache entries (one for the user and another for the role).  
* Allow second, minute, day, month, year... as durations. 
  In the initial code all limitations are per minute. 
  In order to do this, the number of requests in settings should be transformed into something like `60/min` or `1000/day`. 
  The code could parse that value and calculate the appropriated duration of the cache in seconds from that value. 
* Add a middleware class in addition to the decorator. 
  If we want to apply the date limitation to all views, then is better to create a middleware class that applies it to all requests, instead of decorating every single view.

## 3. How to install

There's a `docker-compose.yml` file that will allow you to start the test server without having to install any additional software (only docker).

In order to run the test server, execute:

```
$ cd weathersite
$ docker-compose up -d
```

Wait until the container is built and running (or run the command without the `-d` flag to see the progress).
Now the server should be running and ready to accept requests.

In order to test with authenticated users, I've created a fixture to create test data (actually, a user for authentication).
This data can be installed doing:

```
$ docker exec -it weatherapi python manage.py loaddata auth.json
Installed 25 object(s) from 1 fixture(s)
```

After that your database (a simple SQLite for testing) will contain a user to test authenticated requests.

- Username: `admin@example.test`
- Password: `test`

## 4. Tests

You can test the API in two different ways:

### 4.1 Automatic tests

There are 2 automatic integration tests for the limited endpoint (located in `/weather/tests.py`), one for anonymous (limited) requests and another for authenticated requests.
In order to run the tests you can execute:

```
$ docker exec -it weatherapi python manage.py test weather
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..
----------------------------------------------------------------------
Ran 2 tests in 0.219s

OK
```

### Postman collection
There's a postman collection called `Weather-rate limit.postman_collection.json` in the root folder that contains requests for limited (authenticated and anonymous) and unlimited endpoints.

If you select the anonymous limited request and click on "Send", you'll see the response headers contain the new headers.

![Test result](Postman_test.png "Test result")

#### Authenticated requests
The authentication system I use is JWT tokens, so you'll have first to retrieve a valid token using the authentication endpoint. 
There's a request called "JWT get token" (`POST /api/token/`) in the postman collection for that purpose.

The result of the auth request (POST) is something like:

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTYyMTY5MzYxMSwianRpIjoiMmUxN2VjYzBlMjY2NGZhYWEwZjU2ZGUzNDMxZWFhNzUiLCJ1c2VyX2lkIjoxfQ.RnTffXp_WuqC_tW53p8Xs8Wn6moAaezPNiErkqU31_U",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjIwMzk3NjExLCJqdGkiOiJiZDRmMmU0YjkwMTM0Njc4OTVjODkyYTYyZjA3ZGMyOCIsInVzZXJfaWQiOjF9.atv4UAs_1dUmajGiJ7xmx6ae5ycI0_Z7UD25P2Lta30"
}
```

You have to copy the `access` token and paste it in the `Authentication` header in the authenticated request, with the prefix `Bearer `.

#### Run requests several times
Postman allows you to run a request several times, so you can test the rate limitation actually works. 
In order to do that:

- Click on the ellipsis button on the collection, and select "Run collection".
- Select only the anonymous limited request.
- Set 61 iterations.
- Click on run.
- You'll see the last request fails with a 429.

Of course, you can send the request manually 61 times and check how the headers change, but it will take more time... 


