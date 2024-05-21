#!/bin/bash

set -e
set -x

./test.sh

td-plenaries-markdown 2>&1 >out/td-plenaries-markdown.out 
td-plenaries-json 2>&1 >td-plenaries-json
td-votes-json 2>&1 >td-votes-json
td-politicians-json 2>&1 >td-politicians-json
td-print-politicians-by-fraction 2>&1 >td-print-politicians-by-fraction
td-download-referenced-documents 2>&1 >td-download-referenced-documents

echo All is good

