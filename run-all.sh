#!/bin/bash

set -e
set -x

#./test.sh

# If you are executing the below manually, command by command, on the terminal,
# you can leave out the output redirection >out... and 2>&1 etc,
# so you see the output just printed on the terminal.
# All td scripts used below are defined in setup.py.
mkdir -p out
./download-actors.sh
td politicians json >out/td-politicians-json 2>&1
./download-plenaries.sh
td plenaries json >out/td-plenaries-json 2>&1
td plenaries votes-json >out/td-votes-json 2>&1
td politicians print-by-party >out/td-print-politicians-by-party 2>&1

td-download-referenced-documents >out/td-download-referenced-documents 2>&1
./convert-documents-to-text.sh

# summarizing (just for reference, managing the summarization process is still pretty ad hoc)
# temporarily add a filter for documents to pick up in the summarize.py script, if you only want to summarize a few specific ones.
#td-summarize 0 1000
#td-summarize 1000 2000
#td-summarize 1000 100000
#td-summaries-json


echo All is good

