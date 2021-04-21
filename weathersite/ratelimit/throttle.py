import functools
import time

from django.conf import settings
from django.core.cache import cache as default_cache
from django.utils.translation import gettext_lazy as _

from ipware import get_client_ip

from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated
from rest_framework.response import Response

DEFAULT_DURATION = 60  # default is requests per minute
NUMBER_OF_REQUESTS = getattr(settings, "DEFAULT_RATE_LIMIT_PER_MINUTE", 60)


class RateExceeded(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("Rate limit exceeded")


def get_cache_key(request):
    """
    Identify the machine making the request by parsing several headers like
    HTTP_X_FORWARDED_FOR or REMOTE_ADDR.
    Using ipware library for that (see https://github.com/un33k/django-ipware).
    """
    client_ip, is_routable = get_client_ip(request)
    # not routable addresses are private
    return client_ip


def check_rate_limit(request, number_of_requests=None):
    """
    Implement the check to see if we should apply throttling to the request.
    For authenticated requests there's no rate limit check
    Returns a tuple (Result, Current rate limit, Remaining calls):
        - Result True -> request requires throttling and it was accepted
                  False -> request doesn't requires rate limit (i.e. authenticated user)
        - Current rate limit -> If the request requires throttling, the current rate limit
        - Remaining calls -> If the request requires throttling, the remaining calls allowed
    Exceptions:
        On rate limit exceeded raises a RateExceeded exception
        When the client IP can't be retrieved, returns a HTTP 401
    """

    if request.user.is_authenticated:
        return False, None, None  # Only throttle unauthenticated requests.

    cache_key = get_cache_key(request)
    if cache_key is None:  # can't retrieve the IP
        raise NotAuthenticated()

    duration = DEFAULT_DURATION
    number_of_requests = number_of_requests or NUMBER_OF_REQUESTS
    history = default_cache.get(cache_key, [])
    now = time.time()

    # Drop any requests from the history which have "now" passed the
    # throttle duration
    while history and history[-1] <= now - duration:
        history.pop()
    if len(history) >= number_of_requests:
        raise RateExceeded()
    else:
        # accepted
        history.insert(0, now)
        default_cache.set(cache_key, history, duration)
        return True, number_of_requests, number_of_requests - len(history)


# decorator for views

def with_rate_limit(number_of_requests: int = NUMBER_OF_REQUESTS):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(request, *args, **kwargs):
            try:
                throttled, limit_requests, pending_requests = check_rate_limit(request, number_of_requests)
                response = function(request, *args, **kwargs)
                if throttled:
                    # add throttling response headers
                    response["X-CURRENT-RATE-LIMIT"] = limit_requests
                    response["X-REMAINING-CALLS"] = pending_requests
                return response
            except RateExceeded:
                return Response(status=status.HTTP_429_TOO_MANY_REQUESTS)
        return wrapper
    return decorator
