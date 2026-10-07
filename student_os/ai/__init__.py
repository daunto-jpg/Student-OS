"""Partition C - AI Integration.

  C1 (AI lead):   config.py, errors.py, prompts.py, gemini_client.py
  C2:             context_builder.py, router.py, assistant.py

Rules for this package:
  * Read-only. Nothing here writes to the database. Python collects the data
    and builds the text; Gemini only ever receives text.
  * Importing this package never imports the Gemini SDK and never touches the
    network, so the rest of the app (and every test) works offline.
  * The API key lives in an environment variable / .env file only.
"""
