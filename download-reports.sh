#!/bin/bash

download_plenary_report_pdf() {
  to=${1:300}
  mkdir data/input/plenary/pdf
  for i in $(seq -w 300); do
    curl https://www.dekamer.be/doc/PCRI/pdf/55/ip$i.pdf -o data/input/plenary/pdf/ip${i}.pdf
  done
}

download_plenary_report_html() {
  to=${1:300}
  mkdir data/input/plenary/html
  for i in $(seq -w 300); do
    curl https://www.dekamer.be/doc/PCRI/html/55/ip${i}x.html -o data/input/plenary/html/ip${i}x.html
  done
}

max_plenary_nr=${1:-300}
# download_plenary_report_pdf ${max_plenary_nr}
download_plenary_report_html ${max_plenary_nr}
