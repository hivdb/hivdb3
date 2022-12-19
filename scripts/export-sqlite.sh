#! /bin/bash

set -e

VERSION=$1

python3 -m hivdb3.entry db-to-sqlite "postgresql://postgres@hivdb3-devdb:5432/postgres" /dev/shm/hivdb3-$VERSION.db --all
echo "build/hivdb3-$VERSION.db"
ln -s hivdb3-$VERSION.db /dev/shm/hivdb3-latest.db
(ls -1 ./views/*.sql 2>/dev/null || true) | sort -h | while read filepath; do
    sqlite3 /dev/shm/hivdb3-latest.db < $filepath
done
echo "build/hivdb3-latest.db -> hivdb3-$VERSION.db"

mkdir -p build/
mv /dev/shm/*.db build/
