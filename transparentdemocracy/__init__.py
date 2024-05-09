import os

from config import CONFIG

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

# output
PLENARY_MARKDOWN_OUTPUT_PATH = os.path.join(DATA_PATH, "output", "plenary", "markdown")
PLENARY_JSON_OUTPUT_PATH = os.path.join(DATA_PATH, "output", "plenary", "json")
ENRICHED_VOTES_JSON_OUTPUT_PATH = os.path.join(DATA_PATH, "output", "plenary", "enriched-json")
POLITICIANS_JSON_OUTPUT_PATH = os.path.join(DATA_PATH, "output", "politician")
