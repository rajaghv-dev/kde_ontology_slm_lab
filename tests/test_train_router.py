"""Unit tests for the rule-based KDE task router.

The router is pure-python regex/keyword logic — these tests run in CI on
CPU with no extras installed.
"""
from src.training.train_router import ADAPTERS, explain, route


def test_returns_one_of_the_seven_adapters():
    out = route("anything goes here")
    assert out in ADAPTERS


def test_architecture_default_fallback():
    # An empty / no-keyword query should fall back to the broadest adapter.
    assert route("") == "architecture"
    assert route("   ") == "architecture"


def test_architecture_explicit():
    assert route("how does the indexing component work overall?") == "architecture"


def test_debugging_route():
    assert route("Plasma freezes when I open a folder") == "debugging"
    assert route("why does kded crash on login") == "debugging"


def test_code_navigation_route():
    assert route("Which class emits resultsReady?") == "code_navigation"
    assert route("where is KFileSearchBackend defined") == "code_navigation"


def test_tool_use_route():
    assert route("Run journalctl --user -u plasmashell to see the log") == "tool_use"
    assert route("invoke ctest --output-on-failure -R minisearch") == "tool_use"


def test_patch_review_route():
    assert route("review this diff and tell me if it regresses search") == "patch_review"
    assert route("apply this patch to fix the freeze") == "patch_review"


def test_qml_cpp_route():
    assert route("How do I expose a Q_PROPERTY to QML?") == "qml_cpp"
    assert route("qmlRegisterType for KFileSearcher backend") == "qml_cpp"


def test_dbus_config_route():
    assert route("Which qdbus methods does the minisearch service expose?") == "dbus_config"
    assert route("Where is the KConfig key MaxResults defined?") == "dbus_config"


def test_route_is_deterministic():
    q = "Why does Plasma crash when I open folders?"
    assert route(q) == route(q) == route(q)


def test_explain_returns_match_metadata():
    info = explain("Plasma freezes on login")
    assert info["adapter"] == "debugging"
    assert info["matched"]
    assert info["rule_index"] >= 0


def test_explain_fallback_has_no_match():
    info = explain("")
    assert info["adapter"] == "architecture"
    assert info["matched"] is None
