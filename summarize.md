# How to summarize documents

## Setup project, follow main readme.md

Hint: you should rerun `pip install -e .`

## Install Ollama

Follow installation here: https://ollama.com/download/mac

## Run summarizer:

`td-summarize 1000 2000`

This will summarize documents where 1000<=byte_size<2000.
You can interrupt this process and resume later. Already summarized documents will not be resummarized.