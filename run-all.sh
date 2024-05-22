#!/bin/bash

set -e
set -x

./test.sh

mkdir -p out
td-plenaries-markdown >out/td-plenaries-markdown.out 2>&1
td-plenaries-json >out/td-plenaries-json 2>&1
td-votes-json >out/td-votes-json 2>&1
td-politicians-json >out/td-politicians-json 2>&1
td-print-politicians-by-fraction >out/td-print-politicians-by-fraction 2>&1
td-download-referenced-documents >out/td-download-referenced-documents 2>&1

./convert-documents-to-text.sh

echo All is good

