#! /bin/bash

DBML2SQL=$(which dbml2sql)
DOS2UNIX=$(which dos2unix)
TARGET_DIR="/build/sqls"
EXPOSE_DIR="build/sqls"

set -e

cd $(dirname $0)/..

function copy_csv() {
  source_csv=$1
  target_table=$2
  cat <<EOF
COPY "$target_table" FROM STDIN WITH DELIMITER ',' CSV HEADER NULL 'NULL';
$(cat $source_csv | dos2unix)
\.

EOF
}

if [ ! -x "$DBML2SQL" ]; then
    npm install -g @dbml/cli
fi

if [ ! -x "$DOS2UNIX" ]; then
    brew install dos2unix
fi

mkdir -p $TARGET_DIR

dbml2sql --postgres schema.dbml > $TARGET_DIR/01_schema.sql

cat >> $TARGET_DIR/01_schema.sql <<EOF
CREATE EXTENSION btree_gist;
EOF

(ls -1 constraints_pre-import/*.sql 2>/dev/null || true) | while read sql; do
  dos2unix $sql
  cat $sql >> $TARGET_DIR/01_schema.sql
done
echo "$EXPOSE_DIR/01_schema.sql"

copy_csv payload/tables/articles.csv articles >> $TARGET_DIR/02_data_tables.sql
copy_csv payload/tables/ref_amino_acid.csv ref_amino_acid >> $TARGET_DIR/02_data_tables.sql
copy_csv payload/tables/drug_classes.csv drug_classes >> $TARGET_DIR/02_data_tables.sql
copy_csv payload/tables/drugs.csv drugs >> $TARGET_DIR/02_data_tables.sql
copy_csv payload/tables/resistance_mutations.csv resistance_mutations >> $TARGET_DIR/02_data_tables.sql

ls -1 payload/tables/isolates.d/*.csv | while read filepath; do
  copy_csv $filepath isolates >> $TARGET_DIR/02_data_tables.sql
done

ls -1 payload/tables/gene_isolates.d/*.csv | while read filepath; do
  copy_csv $filepath gene_isolates >> $TARGET_DIR/02_data_tables.sql
done

ls -1 payload/tables/mutations.d/*.csv | while read filepath; do
  copy_csv $filepath mutations >> $TARGET_DIR/02_data_tables.sql
done

ls -1 payload/tables/invitro_selection/*.csv | while read filepath; do
  copy_csv $filepath invitro_selection >> $TARGET_DIR/02_data_tables.sql
done

ls -1 payload/tables/invitro_selection_drugs/*.csv | while read filepath; do
  copy_csv $filepath invitro_selection_drugs >> $TARGET_DIR/02_data_tables.sql
done

pushd payload/ >/dev/null
if [ -z "$(git status -s .)" ]
then
    mtime=$(git log -1 --date unix . | \grep '^Date:' | \awk '{print $2}')
else
    # echo 'There are uncommited changes under payload/ repository. Please commit your changes.' 1>&2
    # exit 42
    mtime=$(find . -type f -print0 | xargs -0 stat -c %Y | sort -nr | head -1)
fi
export TZ=0
last_update=$(date -d @${mtime} +%FT%TZ)
popd >/dev/null
echo "INSERT INTO last_update (scope, last_update) VALUES ('global', '${last_update}');" >> $TARGET_DIR/02_data_tables.sql

echo "$EXPOSE_DIR/02_data_tables.sql"

echo '' > $TARGET_DIR/03_derived_tables.sql
(ls -1 derived_tables/*.sql 2>/dev/null || true) | sort -h | while read filepath; do
    cat $filepath >> $TARGET_DIR/03_derived_tables.sql
done

(ls -1 constraints_post-import/*.sql 2>/dev/null || true) | while read sql; do
  dos2unix $sql
  cat $sql >> $TARGET_DIR/03_derived_tables.sql
done
echo "$EXPOSE_DIR/03_derived_tables.sql"

rm -rf $EXPOSE_DIR 2>/dev/null || true
mkdir -p $(dirname $EXPOSE_DIR)
mv $TARGET_DIR $EXPOSE_DIR
