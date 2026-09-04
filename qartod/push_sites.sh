#!/usr/bin/env bash
# Run on the production server: mirror ~/codar/sites (raw/ and qartod/) to the test server.
#   ./push_sites.sh        # sync
#   ./push_sites.sh -n     # dry run

rsync -az --delete --prune-empty-dirs "$@" \
    --include='*/' --include='*.ruv' --exclude='*' \
    ~/codar/sites/  test:~/codar/sites/
