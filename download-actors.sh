#!/bin/bash

set -e

download_overview() {
  page=0
  start=0

  while true; do
    echo "downloading page $page"
    curl -fsS --header 'Accept: application/json' "https://data.dekamer.be/v0/actr?start=$start" -o data/input/actors/pages/$page.json
    length=$(cat data/input/actors/pages/$page.json | jq -r '.items | length')

    start=$[start+length]
    page=$[page+1]

    if [ "$length" == "0" ]; then
        return
    fi
  done
}

download_actors() {
  for file in data/input/actors/pages/*.json; do
    for gaabId in $(cat "$file"|jq '.items[].gaabId'); do
      ACTOR_JSON="data/input/actors/actor/$gaabId.json"
      if [ ! -e "$ACTOR_JSON" ]; then
        echo "downloading $gaabId"
        curl -fsS --header 'Accept: application/json' "https://data.dekamer.be/v0/actr/$gaabId" -o "$ACTOR_JSON"
      fi
    done
  done
}

mkdir -p data/input/actors/pages
mkdir -p data/input/actors/actor
download_overview
download_actors
