"""
--------------------------------------------------------------------------------
File        : core/services/ai/__init__.py
Purpose     : Expose AI service primitives for provider and safety integration.

Responsibilities:
    - Mark the AI service package as importable.
    - Keep provider, safety, and data-transfer modules grouped together.

Flow:
    Controllers or future read-only AI tools
        ->
    core.services.ai modules

Used By:
    - future read-only AI controllers and tools

Returns:
    None.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations
