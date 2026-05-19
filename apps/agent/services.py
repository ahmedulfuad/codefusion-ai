from apps.common.services import BaseService
from .models import ResearchSession, Repository


class AgentService(BaseService):
    model = ResearchSession

    def get_session_queryset(self):
        """
        Returns the base optimized queryset for ResearchSessions.
        """
        return self.model.objects.all().select_related('repository').prefetch_related('findings')

    def get_session_queryset_by_repo_url(self, repo_url):
        """
        Returns the base optimized queryset for ResearchSessions filtered by repository URL.
        """
        return self.get_session_queryset().filter(repository__url=repo_url)

    def get_session_queryset_by_multi_params(self, **kwargs):
        """
        Returns the base optimized queryset for ResearchSessions filtered by multiple parameters.
        """
        return self.get_session_queryset().filter(**kwargs)

    def create_research_session(self, **kwargs):
        """
        Creates a new ResearchSession and its associated Repository if needed.
        """
        repository_url = kwargs.pop("repository_url", "")
        repository_name = kwargs.pop("repository_name", "")
        question = kwargs.pop("question", "")

        # Get or create the repository record
        repository, created = Repository.objects.get_or_create(
            url=repository_url,
            defaults={"name": repository_name}
        )
        
        # Check if the question for the URL already existed then return the session
        existed_session = self.get_session_queryset_by_multi_params(**{
            "repository__url": repository.url,
            "question": question,
        })
        if existed_session.exists():
            return existed_session.first()
        
        # Create the session linked to this repository
        session = self.create(repository=repository, question=question, **kwargs)
        
        # Placeholder for the actual AI triggering
        session.final_answer = "This is a placeholder answer. The AI agent will be wired up in Step 4!"
        session.save(update_fields=['final_answer'])
        
        return session
