import pytest

from docs_qa.auth.api_key import MissingApiKeyError, role_for_key
from docs_qa.auth.role import Role
from docs_qa.settings import AuthSettings, Settings

SETTINGS = Settings(
    auth=AuthSettings(api_keys={"editor-key": Role.EDITOR, "reader-key": Role.READER})
)


def test_known_key_maps_to_its_role() -> None:
    assert role_for_key("reader-key", SETTINGS) is Role.READER


@pytest.mark.parametrize("api_key", [None, "", "wrong-key"])
def test_unknown_or_missing_key_is_rejected(api_key: str | None) -> None:
    with pytest.raises(MissingApiKeyError):
        role_for_key(api_key, SETTINGS)
