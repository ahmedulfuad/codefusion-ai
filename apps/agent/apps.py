from django.apps import AppConfig


class AgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agent'

    def ready(self):
        """
        This method runs once when Django starts.
        Importing the signals module here ensures the @receiver decorators are registered.
        """
        import apps.agent.signals
