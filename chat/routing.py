from django.urls import path

from . import consumers

websocets_URLpatterns = [
    path('ws/<uuid:room_id>/' , consumers.ChatConsumer.as_asgi())
]