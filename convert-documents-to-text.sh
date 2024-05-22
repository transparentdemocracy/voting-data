#!/bin/bash

function convert_parallel() {
  find data/input/documents -name "*.pdf" | parallel pdftotext
}

function convert_noparallel() {
  find data/input/documents -name "*.pdf" -exec pdftotext {} ';'
}

function convert_documents() {
    if ! which pdftotext > /dev/null; then
        echo "pdftotext is missing; try running brew install poppler"
    fi
    if which parallel >/dev/null; then
        convert_parallel
    else
        echo "parallel not found. Will fun without parallellism Install using `brew install parallel` to speed things up"
        convert_noparallel
    fi
}
