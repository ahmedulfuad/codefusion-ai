import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ResearchSession

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
