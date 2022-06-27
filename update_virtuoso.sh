#!/bin/bash

set -e              # exit if any command fails
start_time=`date +%s`

docker-compose down

# Build and run parser
docker build -t col-parser col_parser/
docker run \
    --name col-parser \
    --rm \
    -v "col_cache:/root/cache" \
    -v "dataexchange:/root/data" \
    col-parser \
    bash download_and_parse.sh $1

# Run import container
docker run \
    --name virtuoso_dataimport \
    -d \
    --rm \
    --env-file virtuoso.env \
    -v "dataexchange:/dataexchange" \
    -v "virtuoso_data:/data" \
    tenforce/virtuoso

sleep 40 # Wait for import container to start sql server


# Bulk import ontology and data
ONTOLOGY="ontology_$(date +'%F_%T').ttl" # Renamng file to unique name because virtuoso doesn't support importing the same filepath twice
PARSED="parsed_$(date +'%F_%T').nt"
DATA_GRAPH_IRI="http://col.htwk-leipzig.de"
ONTO_GRAPH_IRI="http://ontology.col.htwk-leipzig.de"
docker cp ontology.ttl "virtuoso_dataimport:/data/dumps/$ONTOLOGY" # Copy ontology to server for import
cat <<EOF | docker exec --interactive virtuoso_dataimport sh
mv /dataexchange/parsed.nt "/data/dumps/$PARSED"

# Drop graph, if existent
isql-v exec="
    log_enable(3,1);
    SPARQL DROP SILENT GRAPH <$ONTO_GRAPH_IRI>;
    SPARQL DROP SILENT GRAPH <$DATA_GRAPH_IRI>;
"

# Bulk load graphs
isql-v exec="
    ld_dir ('dumps', '$ONTOLOGY', '$ONTO_GRAPH_IRI');
    ld_dir ('dumps', '$PARSED', '$DATA_GRAPH_IRI');
"
for i in {1..4}
do
    isql-v exec="rdf_loader_run();" &
done
wait
isql-v exec="checkpoint;"

# Show results + cleanup
isql-v exec="select ll_file, ll_graph, ll_started, ll_done, ll_state, ll_error from DB.DBA.LOAD_LIST;"
isql-v exec="sparql select (count(*) as ?Number_of_Tripples) from <$DATA_GRAPH_IRI> where {?s ?p ?o};"
rm "/data/dumps/$PARSED" "/data/dumps/$ONTOLOGY"
EOF

docker stop virtuoso_dataimport

docker volume rm dataexchange

docker-compose up -d

echo "Took $((`date +%s`-start_time)) seconds ($(((`date +%s`-start_time)/60)) minutes)."
