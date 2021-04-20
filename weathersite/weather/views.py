from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view()
def limited(request):
    return Response({"message": f"Limited endpoint! {request.user}"})


@api_view()
def unlimited(request):
    return Response({"message": "Unlimited endpoint!"})
