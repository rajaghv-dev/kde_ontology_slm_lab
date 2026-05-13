"""Task classifier that routes an incoming prompt to one of seven KDE adapters.

The project plan describes a *mixture of LoRA experts*: one adapter per
KDE task family. At inference time a tiny router decides which adapter to
load. We deliberately keep that router **rule-based** in v0:

* It runs on CPU in microseconds.
* It is fully deterministic and unit-testable.
* It does not need any of the training extras to ship.

When the lab eventually graduates to a learned router (e.g. a 30M-param
distilbert classifier fine-tuned on a labelled prompt set), this module's
``route()`` becomes the *fallback* and the learned model's confidence gates
the choice.

The seven adapters
------------------
* ``architecture``     — "how does X work", component diagrams, ontology Q&A
* ``debugging``        — "why does X freeze", log triage, symptom-to-cause
* ``code_navigation``  — "where is X defined", "which class emits Y"
* ``tool_use``         — qdbus / journalctl / ctest invocations
* ``patch_review``     — diffs, fix-it suggestions, regression analysis
* ``qml_cpp``          — QML <-> C++ bindings, qmlRegisterType
* ``dbus_config``      — D-Bus services, KConfig keys, .desktop files
"""
from __future__ import annotations

import re

ADAPTERS = (
    "architecture",
    "debugging",
    "code_navigation",
    "tool_use",
    "patch_review",
    "qml_cpp",
    "dbus_config",
)

# Keywords are matched case-insensitively against the query. The *order*
# matters: we evaluate the most specific *symptom-y* tasks first (debugging,
# patch review) before the structural ones (qml, dbus_config), and fall
# back to ``architecture`` (the broadest of the seven) if nothing matches.
#
# Tie-breaking note: queries like "why does kded crash on login" contain
# both a debug verb ("crash") and a dbus_config token ("kded"). We rank
# debugging higher because the *symptom* is the thing the user is actually
# asking about; the named subsystem is just where it happens.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    # Patch review fires first: phrases like "apply this patch to fix the
    # freeze" mention both a debug verb *and* a code-change verb. The user's
    # primary intent is the patch.
    ("patch_review", re.compile(
        r"\b(diff|patch|review|regress(?:ion)?|fix\s*me|fix-it|revert|hunk)\b",
        re.I)),
    ("debugging", re.compile(
        r"\b(crash|crashes|crashed|freeze|freezes|hang|hangs|stuck|leak|leaks|"
        r"slow|slower|slowness|why\s+does|why\s+is|symptom|"
        r"segfault|stack\s*trace|log\s*category|qcdebug)\b",
        re.I)),
    ("qml_cpp", re.compile(
        r"\b(qml|qmlregistertype|q_property|q_invokable|qquick)\b",
        re.I)),
    ("dbus_config", re.compile(
        r"\b(dbus|qdbus|kconfig|kconfigxt|\.desktop|servicetype|kded|"
        r"kshared(?:config)?|configgroup|configkey|max(?:results)?)\b",
        re.I)),
    ("tool_use", re.compile(
        r"\b(journalctl|ctest|gdb|valgrind|strace|systemctl|invoke|"
        r"kcmshell|kbuildsycoca)\b",
        re.I)),
    ("code_navigation", re.compile(
        r"\b(where\s+is|which\s+(?:class|file|signal|slot|method)|"
        r"locate|defines?|declared?|implementation\s+of|"
        r"emit(?:s|ted)?|connects?\s+to|callers?\s+of)\b",
        re.I)),
    ("architecture", re.compile(
        r"\b(architecture|design|component|module|how\s+does|how\s+is|"
        r"what\s+is|overview|relationship|depend(?:s|ency))\b",
        re.I)),
]


def route(query: str) -> str:
    """Return the adapter name best matching ``query``.

    Determinism: first rule that matches wins. If nothing matches, we return
    ``"architecture"`` — the broadest adapter is the safest default because
    architecture-style answers are at worst verbose, never wrong-domain.
    """
    if not query or not query.strip():
        return "architecture"
    for adapter, pat in _RULES:
        if pat.search(query):
            return adapter
    return "architecture"


def explain(query: str) -> dict:
    """Diagnostic helper: which rule (if any) fired, and what was matched.

    Useful for the example runner and for debugging routing mistakes.
    """
    for adapter, pat in _RULES:
        m = pat.search(query or "")
        if m:
            return {"adapter": adapter, "matched": m.group(0), "rule_index": _RULES.index((adapter, pat))}
    return {"adapter": "architecture", "matched": None, "rule_index": -1}
