from django.views.generic import TemplateView
from rest_framework import generics, status
from rest_framework.response import Response
from apps.common.pagination import CustomCursorPagination
from .serializers import (
    ResearchSessionSerializer,
    ResearchSessionInputSerializer,
)
from .services import AgentService


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET: List past sessions (filter by ?repository_url=...)
    POST: Start a new research session
    """
    service_class = AgentService
    serializer_class = ResearchSessionSerializer
    input_serializer_class = ResearchSessionInputSerializer
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        # Fetch the optimized queryset from the Service layer
        repo_url = self.request.query_params.get('repository_url')
        if repo_url:
            queryset = self.service_class().get_session_queryset_by_repo_url(repo_url)
        else:
            queryset = self.service_class().get_session_queryset()

        return queryset

    def create(self, request, *args, **kwargs):
        input_serializer = self.input_serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated_data = input_serializer.validated_data
        
        # Call the service
        session = AgentService().create_research_session(**validated_data)
        
        return Response(
            data=self.serializer_class(session).data,
            status=status.HTTP_201_CREATED
        )


class SessionRetrieveView(generics.RetrieveAPIView):
    """
    GET: Retrieve exact results and findings of a specific session
    """
    service_class = AgentService
    serializer_class = ResearchSessionSerializer
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        # Fetch the optimized queryset from the Service layer
        return self.service_class().get_session_queryset()


class AgentDashboardView(TemplateView):
    template_name = "dashboard.html"
