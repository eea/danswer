import pytest
from unittest.mock import MagicMock, patch
from onyx.server.eea_config.eea_config_backend import get_eea_config, set_eea_config
from onyx.server.eea_config.models import Config_EEA
from onyx.key_value_store.interface import KvKeyNotFoundError

@patch("onyx.server.eea_config.eea_config_backend.get_kv_store")
def test_get_eea_config_not_found(mock_get_kv_store):
    print("\n[Feature 1]: Testing getting EEA Config when it does not exist (fallback to empty JSON) -> OK")
    mock_store = MagicMock()
    mock_store.load.side_effect = KvKeyNotFoundError()
    mock_get_kv_store.return_value = mock_store

    result = get_eea_config()
    assert isinstance(result, Config_EEA)
    assert result.config == "{}"

@patch("onyx.server.eea_config.eea_config_backend.get_kv_store")
def test_get_eea_config_found(mock_get_kv_store):
    print("\n[Feature 1]: Testing getting EEA Config when it exists -> OK")
    mock_store = MagicMock()
    mock_store.load.return_value = '{"disclaimer": "test"}'
    mock_get_kv_store.return_value = mock_store

    result = get_eea_config()
    assert result.config == '{"disclaimer": "test"}'

@patch("onyx.server.eea_config.eea_config_backend.get_kv_store")
def test_set_eea_config(mock_get_kv_store):
    print("\n[Feature 1]: Testing setting EEA Config -> OK")
    mock_store = MagicMock()
    mock_get_kv_store.return_value = mock_store

    request = Config_EEA(config='{"disclaimer": "new test"}')
    result = set_eea_config(request=request, _=MagicMock())

    assert result == {"Status": "OK"}
    mock_store.store.assert_called_once_with("eea_custom_config", '{"disclaimer": "new test"}')
