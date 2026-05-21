from django.urls import path
from . import views

# Required for the 'namespace' param
app_name = 'apps.agent'


urlpatterns = [
    path(
        'sessions/',
        views.SessionListCreateView.as_view(),
        name='session-list-create'
    ),
    path(
        'sessions/<int:pk>/',
        views.SessionRetrieveView.as_view(),
        name='session-detail'
    ),
]
