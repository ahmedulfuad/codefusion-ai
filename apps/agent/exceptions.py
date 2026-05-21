from django.utils.translation import gettext_lazy as _
from rest_framework import status
# Import from DRF exceptions to natively utilize its serializer engine
from rest_framework.exceptions import APIException


class AgentExecutionFailedException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("An error occurred while connecting to the AI service.")
    default_code = "AGENT_EXECUTION_FAILED"

    def __init__(self, message=None, *args, **kwargs):
        error_message = message or self.default_detail
        # Structuring self.detail as a dictionary forces DRF to unpack
        # both keys into the root level of your final JSON response body.
        self.detail = {
            "detail": error_message,
            "code": self.default_code
        }
        # Keep properties intact for compatibility if accessed elsewhere in code
        self.message = error_message
        self.code = self.default_code
