#!/bin/bash
set -euo pipefail

RESULTS_DIR_BASE="reports/allure-results"
COMBINED_RESULTS_DIR="reports/allure-results-all"

rm -rf "${RESULTS_DIR_BASE}" "${COMBINED_RESULTS_DIR}"
mkdir -p "${RESULTS_DIR_BASE}"

for browser in chromium firefox webkit; do
  browser_results_dir="${RESULTS_DIR_BASE}/${browser}"
  rm -rf "${browser_results_dir}"
  mkdir -p "${browser_results_dir}"
  pytest --browser="${browser}" --alluredir="${browser_results_dir}" --clean-alluredir
done

mkdir -p "${COMBINED_RESULTS_DIR}"
for browser_dir in "${RESULTS_DIR_BASE}"/*; do
  cp -a "${browser_dir}/." "${COMBINED_RESULTS_DIR}/"
done

if [ -z "$(ls -A "${COMBINED_RESULTS_DIR}")" ]; then
  echo "Combined Allure results directory is empty: ${COMBINED_RESULTS_DIR}" >&2
  echo "No tests produced Allure results. Check pytest output above." >&2
  exit 1
fi

allure serve "${COMBINED_RESULTS_DIR}"
