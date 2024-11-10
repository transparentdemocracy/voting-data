#!/bin/bash

set -e

if [ -z "$LEGISLATURE" ]; then
    echo "LEGISLATURE is not set. Set LEGISLATURE=56 for current legislature."
    exit 1
fi

download_plenary_reports_html() {
  to=${1}
  HTML_DIR="data/input/plenary/html/leg-${LEGISLATURE}"
  mkdir -p "$HTML_DIR"
  for i in $(seq -w -f "%03g" "$to"); do
    HTML_PATH="${HTML_DIR}/ip${i}x.html"
    echo "$HTML_PATH"
    if [ ! -e "$HTML_PATH" ]; then
      echo "Downloading $HTML_PATH"
      URL="https://www.dekamer.be/doc/PCRI/html/${LEGISLATURE}/ip${i}x.html"
      curl "$URL" -o "$HTML_PATH"
    fi
  done
}

max_plenary_nr=${1:-11}
download_plenary_reports_html ${max_plenary_nr}
