#!/bin/bash
set -euo pipefail

RESULTS_DIR="reports/allure-results"

rm -rf "${RESULTS_DIR}"
mkdir -p "${RESULTS_DIR}"

pytest --alluredir="${RESULTS_DIR}"

if [ -z "$(ls -A "${RESULTS_DIR}")" ]; then
  echo "Allure results directory is empty: ${RESULTS_DIR}" >&2
  echo "No tests produced Allure results. Check pytest output above." >&2
  exit 1
fi

allure serve "${RESULTS_DIR}"
