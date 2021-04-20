from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view()
def limited(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    remote_addr = request.META.get('REMOTE_ADDR')
    print(f"xff {xff}")
    print(f"remote_addr {remote_addr}")
    return Response({"message": f"Limited endpoint! {request.user}"})


@api_view()
def unlimited(request):
    return Response({"message": "Unlimited endpoint!"})
