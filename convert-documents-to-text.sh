#!/bin/bash

function convert_documents() {
    if ! which pdftotext > /dev/null; then
        echo "pdftotext is missing; try running brew install poppler"
    fi

    find data/input/documents -name "*.pdf" | xargs -P 8 -I {} ./convert-single.sh {}

    rsync -av --include="*/" --include="*.txt" --exclude="*" data/input/documents/ data/output/documents/txt/
    find data/input/documents -name "*.txt" -delete

}

#convert_documents

echo "Counting words (output in data/output/documents/word_counts.info)"
wc -w $(find data/output/documents/txt -name "*.txt" -type f) > data/output/documents/word_counts.info

