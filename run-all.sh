#!/bin/bash

set -e
set -x

#./test.sh

mkdir -p out
td politicians json >out/td-politicians-json 2>&1
td plenaries json >out/td-plenaries-json 2>&1
td plenaries votes-json >out/td-votes-json 2>&1
td politicians print-by-party >out/td-print-politicians-by-party 2>&1

td-download-referenced-documents >out/td-download-referenced-documents 2>&1
./convert-documents-to-text.sh

# summarizing (just for reference, managing the summarization process is still pretty ad hoc)
#td-summarize 0 1000
#td-summarize 1000 2000
#td-summaries-json


echo All is good

