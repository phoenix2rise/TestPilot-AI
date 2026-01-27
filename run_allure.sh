#!/bin/bash
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
