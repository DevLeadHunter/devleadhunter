"""Self-contained demo-site templates.

Each template lives in its own module here and exposes a stable surface
(``TEMPLATE_META``, ``build_content``, ``BODY_COMPONENTS``, ``COMPONENT_SCHEMAS``)
so it can be registered by the shared services without bloating them — and so
several templates can coexist without overwriting each other.
"""
