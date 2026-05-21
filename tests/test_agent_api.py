import pytest
import logging
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, MagicMock

from apps.agent.models import Repository, ResearchSession
from .factories import RepositoryFactory, ResearchSessionFactory, FindingFactory

# Apply database access permission globally across all tests in this file
pytestmark = pytest.mark.django_db


def test_list_past_research_sessions(api_client):
    """
    Verify that a GET request safely reads and outputs past sessions.
    """
    # Arrange: Build mock persistence items via factory
    session = ResearchSessionFactory()
    url = reverse("api_v1:apps.agent:session-list-create")

    # Act: Request list
    response = api_client.get(url)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    results = response.data.get("results") if "results" in response.data else response.data
    assert len(results) == 1
    assert results[0]["question"] == session.question


def test_retrieve_specific_research_session_details(api_client):
    """
    Verify fetching a single session profile resource maps deep nested relationships (findings).
    """
    # Arrange
    session = ResearchSessionFactory()
    finding = FindingFactory(session=session, tool_name="read_github_file")
    url = reverse("api_v1:apps.agent:session-detail", kwargs={"pk": session.id})

    # Act
    response = api_client.get(url)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == session.id
    assert response.data["final_answer"] == session.final_answer
    assert len(response.data["findings"]) == 1
    assert response.data["findings"][0]["tool_name"] == "read_github_file"


@patch("apps.agent.engine.genai.GenerativeModel")
def test_create_research_session_execution_success(mock_generative_model, api_client):
    """
    Verifies that a POST request successfully runs the research loop and counts tokens.
    """
    # Arrange: Mock the Gemini structures completely
    mock_model_instance = MagicMock()
    mock_chat_instance = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = "This repository uses Docker to handle containerization workflows."
    # Emulate parts structures inside candidates for internal calculate_and_add_response_tokens method
    mock_response.candidates = [MagicMock(content=MagicMock(parts=["Mock response token string text chunks"]))]
    
    mock_chat_instance.send_message.return_value = mock_response
    mock_model_instance.start_chat.return_value = mock_chat_instance
    mock_generative_model.return_value = mock_model_instance

    url = reverse("api_v1:apps.agent:session-list-create")
    payload = {
        "repository_url": "https://github.com/validated/pytest-repo",
        "repository_name": "pytest-repo",
        "question": "How does deployment work?"
    }

    # Act
    response = api_client.post(url, data=payload, format="json")

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["final_answer"] == "This repository uses Docker to handle containerization workflows."
    
    # Verify records were generated inside the DB
    assert Repository.objects.filter(url=payload["repository_url"]).exists()
    assert ResearchSession.objects.filter(question=payload["question"]).exists()
    
    created_session = ResearchSession.objects.get(question=payload["question"])
    assert created_session.token_usage > 0


@patch("apps.agent.engine.genai.GenerativeModel")
def test_create_research_session_api_failure_handling(mock_generative_model, api_client):
    """
    Verifies that when the API context crashes, the app returns a 400 Bad Request
    with our structured custom error dictionary.
    """
    # Arrange: Make the mock engine throw a network exception
    mock_model_instance = MagicMock()
    mock_chat_instance = MagicMock()
    mock_chat_instance.send_message.side_effect = Exception("Quota exceeded or Invalid API Key context.")
    
    mock_model_instance.start_chat.return_value = mock_chat_instance
    mock_generative_model.return_value = mock_model_instance

    url = reverse("api_v1:apps.agent:session-list-create")
    payload = {
        "repository_url": "https://github.com/unstable/broken-repo",
        "repository_name": "broken-repo",
        "question": "Will this crash gracefully?"
    }

    # Act
    response = api_client.post(url, data=payload, format="json")

    # Assert custom dictionary Exception structure handling
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.data
    assert "code" in response.data
    assert response.data["code"] == "AGENT_EXECUTION_FAILED"
    assert "Quota exceeded" in response.data["detail"]


def test_research_session_signal_logs_creation(caplog):
    """
    Verifies that the post_save signal triggers and logs correctly
    when a new ResearchSession is created.
    """
    # Tell pytest to capture logs at the INFO level and above
    caplog.set_level(logging.INFO)

    # Trigger the creation of a session (this should fire the post_save signal)
    session = ResearchSessionFactory(question="How do signals work?")

    # Assert that the creation log was successfully written to the log stream
    assert "[SESSION CREATED]" in caplog.text
    assert "How do signals work?" in caplog.text


def test_research_session_signal_logs_update(caplog):
    """
    Verifies that the post_save signal triggers and logs an update
    when an existing ResearchSession is modified.
    """
    # Create the initial session
    session = ResearchSessionFactory()

    # Clear the logs captured during creation so we only test the update
    caplog.clear()
    caplog.set_level(logging.INFO)

    # Update the session (this should fire the 'else' block in your signal)
    session.token_usage = 500
    session.save(update_fields=['token_usage'])

    # Assert the update log was captured
    assert "[SESSION UPDATED]" in caplog.text
    assert "Tokens Used: 500" in caplog.text
