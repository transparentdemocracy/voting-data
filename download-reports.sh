#!/bin/bash

set -e

download_plenary_reports_pdf() {
  to="${1}"
  mkdir -p data/input/plenary/pdf
  for i in $(seq -w "$to"); do
    PDF_PATH="data/input/plenary/pdf/ip${i}.pdf"
    if [ ! -e "$PDF_PATH" ]; then
      echo "Downloading $PDF_PATH"
      curl "https://www.dekamer.be/doc/PCRI/pdf/55/ip$i.pdf" -o "$PDF_PATH"
    fi
  done
}

download_plenary_reports_html() {
  to=${1}
  mkdir -p data/input/plenary/html
  for i in $(seq -w "$to"); do
    HTML_PATH="data/input/plenary/html/ip${i}x.html"
    if [ ! -e "$HTML_PATH" ]; then
      echo "Downloading $HTML_PATH"
      curl "https://www.dekamer.be/doc/PCRI/html/55/ip${i}x.html" -o "$HTML_PATH"
    fi
  done
}

max_plenary_nr=${1:-309}
# download_plenary_reports_pdf ${max_plenary_nr}
download_plenary_reports_html ${max_plenary_nr}
