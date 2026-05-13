"""Build the eval set.

For v0 we hand-author a tiny eval set targeting the symptom embedded in the
mini repo. Each item names the entity that *should* appear in a correct
answer, so the grader is fully programmatic.
"""
from __future__ import annotations


def mini_repo_eval_set() -> list[dict]:
    return [
        {
            "id": "eval:01:signal-emitted",
            "question": "Which signals does the KFileSearcher class emit?",
            "must_mention": ["resultsReady", "searchFailed", "currentPathChanged"],
            "category": "architecture_qa",
        },
        {
            "id": "eval:02:config-key",
            "question": "Which KConfig key controls the maximum number of results in MiniSearch?",
            "must_mention": ["MaxResults"],
            "category": "code_navigation",
        },
        {
            "id": "eval:03:log-category",
            "question": "When MiniSearch becomes slow on large folders, which log category should I enable?",
            "must_mention": ["minisearch.backend"],
            "category": "debugging",
        },
        {
            "id": "eval:04:qml-backend",
            "question": "Which C++ class is the SearchView QML component backed by?",
            "must_mention": ["KFileSearcher"],
            "category": "code_navigation",
        },
        {
            "id": "eval:05:dbus-methods",
            "question": "Which D-Bus methods does org.kde.minisearch expose?",
            "must_mention": ["searchPath", "cancel"],
            "category": "tool_use",
        },
        {
            "id": "eval:06:refusal",
            "question": "What signal does the imaginary class KFooBarMaker emit?",
            "must_not_mention": ["KFooBarMaker emits"],
            "must_mention": ["do not see"],
            "category": "refusal",
        },
    ]
