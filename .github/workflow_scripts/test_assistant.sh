#!/bin/bash

MODULE=integration

set -ex

source $(dirname "$0")/env_setup.sh

setup_test_env

python -m pytest -n 2 -v --capture=tee-sys --log-cli-level=INFO --junitxml=results.xml tests/unittests/$MODULE/
