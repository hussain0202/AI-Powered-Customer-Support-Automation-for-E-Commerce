_config = {"fallback_enabled": True}


def set_fallback(enabled: bool) -> None:
    _config["fallback_enabled"] = bool(enabled)


def is_fallback_enabled() -> bool:
    return _config["fallback_enabled"]
