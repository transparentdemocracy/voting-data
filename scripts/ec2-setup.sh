#!/bin/bash

sudo yum install git
git clone https://github.com/transparentdemocracy/voting-data.git

aws s3 sync s3://karel-dev.transparentdemocracy.eu/txt/ voting-data/data/output/documents/zip/

mkdir -p $HOME/voting-data/data/output/documents
cd $HOME/voting-data/data/output/documents/by-size
for i in zip/*.zip; do
    unzip "$i";
done

cd $HOME/voting-data
python3 -mvenv venv
. venv/bin/activate
pip3 install -r requirements.txt

pip3 install -e .

echo "Start summarizating by running:"
td-summarizer data/output/documents/by-size/txt-group-00.d