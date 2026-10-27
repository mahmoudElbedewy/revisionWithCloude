from django.db.models.signals import post_save , post_delete
from django.dispatch import receiver
from .models import Room , Message
from django.core.cache import cache


@receiver(post_save, sender=Message)
def delete_cache(sender , instance , created , **kwargs):
        room_id = instance.room_id
        cache_key = f'room_messages_{room_id}'
        cache.delete(cache_key)