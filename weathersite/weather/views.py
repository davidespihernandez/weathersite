from rest_framework.decorators import api_view
from rest_framework.response import Response

from ratelimit.throttle import with_rate_limit


@api_view()
@with_rate_limit()
def limited(request):
    return Response({"message": f"Limited endpoint! {request.user}"})


@api_view()
def unlimited(request):
    return Response({"message": "Unlimited endpoint!"})
