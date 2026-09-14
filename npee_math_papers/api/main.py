"""ASGI entrypoint for the NPEE application API."""

from npee_math_papers.api.factory import create_application


app = create_application()
