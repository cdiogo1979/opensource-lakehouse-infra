#!/bin/bash

set -e

SCALE_FACTOR="${TPCH_SCALE_FACTOR:-1}"
OUTPUT_DIR="${TPCH_OUTPUT_DIR:-/opt/tpch/data}"
DBGEN_DIR="/build/dbgen"

echo "========================================"
echo "TPC-H Generator"
echo "Scale factor: ${SCALE_FACTOR}"
echo "Output: ${OUTPUT_DIR}"
echo "========================================"

mkdir -p "${OUTPUT_DIR}"

# Remove previous generated data
rm -f "${OUTPUT_DIR}"/*.tbl

# dbgen expects dists.dss and other source files
# to be in its current working directory.
cd "${DBGEN_DIR}"

echo "Running dbgen..."

./dbgen \
    -f \
    -s "${SCALE_FACTOR}" \
    -C 1 

# dbgen writes the .tbl files into the current directory,
# so move them to the shared output directory.
mv ./*.tbl "${OUTPUT_DIR}/"

echo
echo "========================================"
echo "Generated files"
echo "========================================"

ls -lh "${OUTPUT_DIR}"/*.tbl

echo
echo "TPC-H generation complete."
