#!/bin/sh
# Rebuild the chronicle from what is already downloaded. Downloads are separate, slow (Wayback allows
# ~15 requests/min) and resumable; run them only when adding sources:
#   python3 wayback_mirror.py [site]            pages of lost sites -> mirror/<site>/
#   python3 fetch_images.py fetch && python3 fetch_images.py link      photos of the 3 original archives
#   python3 mirror_images.py fetch && python3 mirror_images.py link    photos of the mirrored sites
#   python3 regional_collect.py && python3 regional_fulltext.py        regional media (up to 2022)
#   python3 video_download.py                   local videos -> $PRYM_ARCHIVE/video
# Publishing: SITE_URL=https://<host>/timeline ./build.sh  (absolute og:image/canonical + sitemap.xml)
set -e
cd "$(dirname "$0")"
python3 clean_article.py && python3 names.py && python3 test_extract.py   # self-checks
python3 extract_articles.py                         # articles.json, timeline/data.json, a/, p/, v/
python3 video_download.py --index                   # timeline/videos.json (local copies of videos)
