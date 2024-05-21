#!/bin/bash

set -e
set -x

#./test.sh

mkdir -p out
td-plenaries-markdown >out/td-plenaries-markdown.out 2>&1
td-plenaries-json >td-plenaries-json 2>&1
td-votes-json >td-votes-json 2>&1
td-politicians-json >td-politicians-json 2>&1
td-print-politicians-by-fraction >td-print-politicians-by-fraction 2>&1
td-download-referenced-documents >td-download-referenced-documents 2>&1

echo All is good

