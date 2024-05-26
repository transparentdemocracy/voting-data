#!/bin/bash

set -e
set -x

cd data/output/documents/txt
find . -type f -exec ls -Sr {} + > ../txt-files.info

cd ..
pwd
file_count="$(cat txt-files.info|wc -l)"
split_size=$[$file_count / 6]
split -d -l "$split_size" txt-files.info txt-group-

mkdir -p by-size
for txt in txt-group-*; do
  rsync -av --files-from="$txt" txt/ "by-size/${txt}/"
  zip "${txt}.zip" -r "by-size/${txt}"
done

