#!/bin/bash

set -e

./test.sh

td-plenaries-markdown
td-plenaries-json
td-votes-json
td-politicians-json
td-print-politicians-by-fraction
td-download-referenced-documents

echo All is good

