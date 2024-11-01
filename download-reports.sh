#!/bin/bash

set -e

if [ -z "LEGISLATURE" ]; then
    echo "LEGISLATURE is not set. Set LEGISLATURE=56 for current legislature."
fi

download_plenary_reports_html() {
  to=${1}
  HTML_DIR="data/input/plenary/html/leg-${LEGISLATURE}"
  mkdir -p "$HTML_DIR"
  for i in $(seq -w "$to"); do
    HTML_PATH="${HTML_DIR}/ip${i}x.html"
    if [ ! -e "$HTML_PATH" ]; then
      echo "Downloading $HTML_PATH"
      curl "https://www.dekamer.be/doc/PCRI/html/${LEGISLATURE}/ip${i}x.html" -o "$HTML_PATH"
    fi
  done
}

max_plenary_nr=${1:-10}
download_plenary_reports_html ${max_plenary_nr}
