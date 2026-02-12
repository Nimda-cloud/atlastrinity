"""Backward-compat shim: brain.message_bus → brain.core.server.message_bus"""
from brain.core.server.message_bus import *  # noqa: F401,F403
