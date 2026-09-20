"""The model layer: one interface (chat, embed, rerank), several backends.

Every named step (find.expand, read.extract, plan.gap, ...) is routed to a
backend and a model by config, never hardcoded at a call site. See
scholium.models.registry.resolve_backend.
"""
