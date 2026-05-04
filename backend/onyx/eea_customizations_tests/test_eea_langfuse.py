import pytest
from unittest.mock import MagicMock, patch
from onyx.utils.eea_utils import get_eea_user_id, eea_start_turn, eea_set_turn_output, _eea_thread_local
from onyx.db.models import ChatMessage

def test_get_eea_user_id():
    print("\n[Feature 2]: Testing Langfuse user ID normalization (stripping API keys and appending persona) -> OK")
    # Test simple stripping and persona suffix
    email = "test@example.com"
    user_id = get_eea_user_id(email, "Default")
    assert user_id == "test@example.com - Default"

    # Test stripping DANSWER_API_KEY_PREFIX correctly
    api_key_email = "api_key__test_key@example.com"
    user_id_key = get_eea_user_id(api_key_email, "Custom")
    assert user_id_key == "test_key - Custom"

def test_eea_start_turn():
    print("\n[Feature 2]: Testing turning initiation (setting up thread local storage context) -> OK")
    # Clear thread local first
    if hasattr(_eea_thread_local, "turn_data"):
        del _eea_thread_local.turn_data

    user_msg = MagicMock(spec=ChatMessage)
    user_msg.id = 123
    user_msg.message = "Hello world"

    eea_start_turn(
        user_message=user_msg,
        user_email="user@test.com",
        persona_name="MyPersona",
        session_id="456",
    )

    data = getattr(_eea_thread_local, "turn_data", None)
    assert data is not None
    assert data["user_message_id"] == 123
    assert data["user_message"] == "Hello world"
    assert data["user_email"] == "user@test.com"
    assert data["persona_name"] == "MyPersona"
    assert data["session_id"] == "456"

@patch("onyx.tracing.framework.create.trace")
@patch("onyx.tracing.framework.create.function_span")
def test_eea_set_turn_output(mock_function_span, mock_trace):
    print("\n[Feature 2]: Testing turning finalization (injecting metadata and recording Langfuse trace) -> OK")
    # Setup thread local state
    _eea_thread_local.turn_data = {
        "user_message_id": 123,
        "user_message": "What is the capital of France?",
        "user_email": "user@test.com",
        "persona_name": "MyPersona",
        "session_id": "456",
    }

    # Assistant message
    assistant_msg = MagicMock(spec=ChatMessage)
    assistant_msg.id = 789
    assistant_msg.message = "Paris"

    # Mock the context managers
    mock_trace.return_value.__enter__.return_value = MagicMock()
    mock_function_span.return_value.__enter__.return_value = MagicMock()

    eea_set_turn_output(assistant_msg)

    # Validate trace call
    mock_trace.assert_called_once()
    trace_kwargs = mock_trace.call_args[1]
    assert trace_kwargs["workflow_name"] == "What is the capital of France?"
    assert trace_kwargs["metadata"]["chat_session_id"] == "456:789"
    assert trace_kwargs["metadata"]["assistant_message_id"] == 789
    assert trace_kwargs["metadata"]["user_email"] == "user@test.com"

    # Validate span call
    mock_function_span.assert_called_once_with(
        name="What is the capital of France?",
        input="What is the capital of France?",
        output="Paris",
    )
