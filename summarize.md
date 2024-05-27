# How to summarize documents

## Setup project, follow main readme.md

Hint: you should rerun `pip install -e .`

## Prepare data

Make sure you have the documents as pdfs files in data/input/documents/pdf/
(You can skip this step if you already have the documents in txt format)
Run `td-download-referenced-documents`

Make sure you have the documents as txt files in data/output/documents/txt/
Run `brew install poppler`. This should install the `pdftotext` command line tool.
Run `convert-documents-to-text.sh`

## Install Ollama

Follow installation here: https://ollama.com/download/mac

## Pull llama3 model

ollama pull llama3

## Run summarizer:

`td-summarize 1000 2000`

This will summarize documents where 1000<=byte_size<2000.
You can interrupt this process and resume later. Already summarized documents will not be resummarized.