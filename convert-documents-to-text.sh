#!/bin/bash

if [ -z "$LEGISLATURE" ]; then
    echo "Missing env var LEGISLATURE (set to 55, 56, ...)"
    exit 1
fi

function convert_documents() {
    if ! which pdftotext > /dev/null; then
        echo "pdftotext is missing; try running brew install poppler"
    fi

    IN_DIR="data/input/documents/leg-${LEGISLATURE}"
    OUT_DIR="data/output/documents/txt/leg-${LEGISLATURE}"
    find "$IN_DIR" -name "*.pdf" | xargs -P 8 -I {} ./convert-single.sh {}

    rsync -av --include="*/" --include="*.txt" --exclude="*" "${IN_DIR}/" "$OUT_DIR"
    find "${IN_DIR}" -name "*.txt" -delete

}

#convert_documents

echo "Counting words (output in data/output/documents/word_counts.info)"
wc -w $(find data/output/documents/txt -name "*.txt" -type f) > data/output/documents/word_counts.info

