"""Readers that walk a KDE-like repo and extract structured information.

Each reader is intentionally simple: regex + standard library. Tree-sitter,
libclang, and friends are upgrade paths but not v0 dependencies — the lab
should be readable in an afternoon.
"""
