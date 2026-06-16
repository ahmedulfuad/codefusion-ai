import logging
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ResearchSession, Finding
from .serializers import ResearchSessionSerializer

# Initialize a standard logger
logger = logging.getLogger(__name__)


@receiver(post_save, sender=ResearchSession)
def log_research_session_save(sender, instance, created, **kwargs):
    """
    Listens for save events on the ResearchSession model.
    'created' is a boolean that is True if a new record was inserted, 
    and False if an existing record was updated.
    """
    if created:
        # Log when a brand new session is created
        logger.info(
            f"[SESSION CREATED] ID: {instance.id} | "
            f"Repo: {instance.repository.name} | "
            f"Question: '{instance.question[:50]}...'"
        )
    else:
        # Log when an existing session is updated (e.g., when final_answer/tokens are saved)
        logger.info(
            f"[SESSION UPDATED] ID: {instance.id} | "
            f"Tokens Used: {instance.token_usage}"
        )


@receiver(post_save, sender=ResearchSession)
def invalidate_session_cache(sender, instance, **kwargs):
    """
    Invalidate the Redis cache for the session detail view whenever a ResearchSession is saved.
    This ensures that users always see the most up-to-date information when retrieving session details.
    """
    cache_key = f"research_session_detail_{instance.id}"
    cache.delete(cache_key)


@receiver(post_save, sender=Finding)
def pre_warm_session_cache(sender, instance, **kwargs):
    """
    After a Finding is saved, we can pre-warm the cache for the associated ResearchSession detail view.
    This is an optimization to ensure that when users retrieve the session details,
    the data is already cached, resulting in faster response times.
    """
    cache.set(
        key=f"research_session_detail_{instance.session.id}",
        value=dict(ResearchSessionSerializer(instance.session).data),
        timeout=60 * 15,   # Cache for 15 minutes
    )
