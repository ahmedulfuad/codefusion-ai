from django.db import models
from apps.common.models import BaseModel


class Repository(BaseModel):
    url = models.URLField(
        unique=True, help_text="The URL of the code repository (e.g., GitHub, GitLab)",
    )
    name = models.CharField(
        max_length=255, blank=True, help_text="A human-friendly name for the repository (optional)",
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['url'], name='idx_repository_url'),
        ]

    def __str__(self):
        return self.url


class ResearchSession(BaseModel):
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name='sessions',
    )
    question = models.TextField(
        help_text="The research question or prompt",
    )
    final_answer = models.TextField(
        null=True, blank=True, help_text="The final synthesized answer to the research question",
    )
    token_usage = models.IntegerField(
        default=0, help_text="The number of tokens used in the research session",
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Speeds up filtering by repo AND sorting by newest sessions simultaneously
            models.Index(fields=['repository', '-created_at'], name='idx_session_repo_created'),
            # Speeds up our global Cursor Pagination sorting by -created_at
            models.Index(fields=['-created_at'], name='idx_session_created_at'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['repository', 'question'], name='unique_session_per_repo_question'
            )
        ]

    def __str__(self):
        return f"Session {self.id} for {self.repository.name}"


class Finding(BaseModel):
    session = models.ForeignKey(
        ResearchSession, on_delete=models.CASCADE, related_name='findings',
    )
    tool_name = models.CharField(
        max_length=100, help_text="The name of the tool used for the finding",
    )
    input_data = models.JSONField(
        help_text="The parameters passed to the tool",
    )
    output_data = models.TextField(
        help_text="The raw output/code returned by the tool",
    )
    conclusion = models.TextField(
        null=True, blank=True, help_text="The agent's synthesized note on this finding",
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Speeds up prefetching findings for a single session chronologically
            models.Index(fields=['session', 'created_at'], name='idx_finding_session_created'),
            # Allows fast analytical queries if you ever want to filter findings by tool type
            models.Index(fields=['tool_name'], name='idx_finding_tool_name'),
        ]

    def __str__(self):
        return f"{self.tool_name} at {self.created_at}"
