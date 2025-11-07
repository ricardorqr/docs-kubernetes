#!/bin/bash

set -x

PDF_DIR=PDFs

# Replace smart quotes and normalize punctuation
sed -i -e "s/’/\'/g" -e "s/–/-/g" -e "s/“/\"/g" -e "s/”/\"/g" "$1.html"

# Re-encode file to proper UTF-8 (drop any bad bytes)
iconv -f utf-8 -t utf-8 -c "$1.html" -o "$1.html.utf8"
mv "$1.html.utf8" "$1.html"

docker run -it --name weasy -d 4teamwork/weasyprint:latest
docker cp codeblock_wrap.css weasy:/tmp/codeblock_wrap.css
docker exec -i weasy weasyprint -v -s /tmp/codeblock_wrap.css '-' '-' >| "$PDF_DIR/$1.pdf" < $1.html
docker stop weasy
docker rm -f weasy
