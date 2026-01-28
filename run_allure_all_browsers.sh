#!/bin/bash
set -euo pipefail

RESULTS_DIR="reports/allure-results"

rm -rf "${RESULTS_DIR}"
mkdir -p "${RESULTS_DIR}"

for browser in chromium firefox webkit; do
  pytest --browser="${browser}" --alluredir="${RESULTS_DIR}"
done

allure serve "${RESULTS_DIR}"
