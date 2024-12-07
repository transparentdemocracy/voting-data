#!/bin/bash

set -e
set -x

# Create output directory if it doesn't exist
mkdir -p out

#./download-actors.sh
#poetry run td politicians json >out/td-politicians-json 2>&1

./download-plenaries.sh
poetry run td plenaries json >out/td-plenaries-json 2>&1
poetry run td plenaries votes-json >out/td-votes-json 2>&1
poetry run td politicians print-by-party >out/td-print-politicians-by-party 2>&1

poetry run td-download-referenced-documents >out/td-download-referenced-documents 2>&1
./convert-documents-to-text.sh

# summarizing (just for reference, managing the summarization process is still pretty ad hoc)
# temporarily add a filter for documents to pick up in the summarize.py script, if you only want to summarize a few specific ones.
#poetry run td-summarize 0 1000
#poetry run td-summarize 1000 2000
#poetry run td-summarize 1000 100000
#poetry run td-summaries-json

echo All is good
