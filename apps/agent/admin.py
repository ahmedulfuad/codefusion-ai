from django.contrib import admin
from apps.agent.models import Repository, ResearchSession, Finding


admin.site.register(Repository)
admin.site.register(ResearchSession)
admin.site.register(Finding)
