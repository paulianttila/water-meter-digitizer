#!/usr/bin/env bash

# To run tests locally
# export CONFIG_FILE=$(PWD)/config/config.ini; ./run_tests.sh
# E.g. export CONFIG_FILE=$(PWD)/test_config/config.ini; ./run_tests.sh

TAVERN_LOG_LEVEL=INFO

# exit when any command fails
set -e

trap "clean_up" EXIT

PWD=$(pwd)

if [ -f "${PWD}/.venv/bin/python" ]; then
  PYTHON="${PWD}/.venv/bin/python"
else
  PYTHON="python3"
fi

TEST_APP_PID=

start_test_app() {
  # start the test app whch use framework
  echo "Start test app"
  cd src
  ${PYTHON} main.py &
  TEST_APP_PID=$!
  echo "PID=${TEST_APP_PID}"
  cd ..

  echo "Waiting for test app to become ready..."
  for i in {1..30}; do
    if curl -s http://localhost:3000/healthcheck | grep -q "Health - OK"; then
      echo "Test app is ready!"
      return 0
    fi
    sleep 0.5
  done
  echo "Warning: Test app did not respond to healthcheck within 15s"
}

run_tests() {
  # add testing_utils.py to tavern tests
  export PYTHONPATH=${PYTHONPATH}:${PWD}/tests/integration/

  # run tests
  ${PYTHON} -m pytest --log-cli-level=${TAVERN_LOG_LEVEL} tests/
}

clean_up() {
  if [ -z "${TEST_APP_PID}" ]; then
    return
  fi
  echo "Stop test app, PID=${TEST_APP_PID}"
  kill -9 ${TEST_APP_PID}
}

echo "Current folder: ${PWD}"

while getopts ":sau" option; do
   case $option in
      s)
        set +e
        ruff check --output-format=github .
        black --check .
        bandit -c pyproject.toml -r .
        exit;;
      a)
        set +e
        start_test_app
        run_tests
        ruff check --output-format=github .
        black --check .
        bandit -c pyproject.toml -r .
        exit;;
      u)
        ${PYTHON} -m pytest tests/unit
        exit;;
   esac
done

start_test_app
run_tests
