# Show available recipes.
default:
    @just --list

# Create local user data/config if needed, then install dependencies.
setup:
    mkdir -p user-data
    if [ ! -f user-data/config.json ]; then cp config.example.json user-data/config.json; fi
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt

# Scan all OPML feeds and build the chronological episode review page.
episodes *args:
    .venv/bin/python fetch_episodes.py {{args}}

# Resolve configured slot names against the OPML feed list.
resolve:
    .venv/bin/python resolve_feeds.py

# Generate the poster PDF and archive its snapshot.
poster:
    .venv/bin/python gen.py

# Start the local browser-based workflow on 127.0.0.1:8765.
web:
    .venv/bin/python server.py

# Run the unit test suite.
test:
    .venv/bin/python -m unittest discover -s tests -v

# Check Python syntax and the local user config JSON.
check:
    .venv/bin/python -m py_compile fetch_episodes.py gen.py resolve_feeds.py server.py webapp.py link_preview.py feed_discovery.py added_feeds.py user_state.py rss_export.py
    .venv/bin/python -m json.tool user-data/config.json > /dev/null
