"""hermes_anchored_edit — content-anchored file tools for Hermes Agent.

Registers three tools:
  smart_patch        single content-anchored edit
  smart_patch_batch  atomic multi-edit (one LLM round-trip)
  read_relevant      targeted slice reading (context frugality)
"""

import logging

from .patch import smart_patch, smart_patch_batch, SMART_PATCH, SMART_PATCH_BATCH
from .read import read_relevant, READ_RELEVANT

logger = logging.getLogger(__name__)


def register(ctx):
    ctx.register_tool(name="smart_patch", toolset="file",
                      schema=SMART_PATCH, handler=smart_patch)
    ctx.register_tool(name="smart_patch_batch", toolset="file",
                      schema=SMART_PATCH_BATCH, handler=smart_patch_batch)
    ctx.register_tool(name="read_relevant", toolset="file",
                      schema=READ_RELEVANT, handler=read_relevant)
    logger.info("hermes_anchored_edit: registered smart_patch, smart_patch_batch, read_relevant")
