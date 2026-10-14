from typing import Any


def pick(doc: Any, path: str) -> Any:
    """Follow a dotted path through nested dicts: pick(d, "a.b.c") is d["a"]["b"]["c"].

    Returns None the moment anything is missing, instead of raising.
    """
    for key in path.split("."):
        if not isinstance(doc, dict):
            return None
        doc = doc.get(key)
    return doc
