#!/usr/bin/env bash

set -e

# --- Configuration & Defaults ---
TAVERN_LOG_LEVEL=${TAVERN_LOG_LEVEL:-INFO}
PWD=$(pwd)
export CONFIG_FILE="${CONFIG_FILE:-${PWD}/test_config/config.ini}"

# --- ANSI Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- Runner / Environment Detection ---
if command -v uv >/dev/null 2>&1; then
  RUNNER="uv run --no-sync"
  PYTHON="uv run --no-sync python"
elif [ -f "${PWD}/.venv/bin/python" ]; then
  RUNNER="${PWD}/.venv/bin"
  PYTHON="${PWD}/.venv/bin/python"
else
  RUNNER=""
  PYTHON="python3"
fi

TEST_APP_PID=

# --- Process Management & Cleanup ---
clean_up() {
  if [ -n "${TEST_APP_PID}" ] && kill -0 "${TEST_APP_PID}" 2>/dev/null; then
    echo -e "${YELLOW}Stopping test app (PID=${TEST_APP_PID})...${NC}"
    kill "${TEST_APP_PID}" 2>/dev/null || kill -9 "${TEST_APP_PID}" 2>/dev/null
    wait "${TEST_APP_PID}" 2>/dev/null || true
  fi
}
trap clean_up EXIT INT TERM

start_test_app() {
  echo -e "${BLUE}Starting test app with CONFIG_FILE=${CONFIG_FILE}...${NC}"
  cd src
  ${PYTHON} main.py &
  TEST_APP_PID=$!
  cd ..
  echo -e "${BLUE}Test app PID: ${TEST_APP_PID}${NC}"

  echo -e "${BLUE}Waiting for test app to become ready...${NC}"
  for i in {1..30}; do
    if ! kill -0 "${TEST_APP_PID}" 2>/dev/null; then
      echo -e "${RED}Error: Test app exited prematurely! Check configuration or port conflicts.${NC}"
      exit 1
    fi
    if curl -s http://localhost:3000/healthcheck | grep -q "Health - OK"; then
      echo -e "${GREEN}✓ Test app is ready!${NC}"
      return 0
    fi
    sleep 0.5
  done
  echo -e "${RED}Error: Test app did not respond to healthcheck within 15s${NC}"
  exit 1
}

# --- Test Suites ---
run_unit_tests() {
  echo -e "${BLUE}Running unit tests...${NC}"
  ${PYTHON} -m pytest tests/unit -v
}

run_integration_tests() {
  start_test_app
  echo -e "${BLUE}Running Tavern integration tests...${NC}"
  export PYTHONPATH=${PYTHONPATH}:${PWD}/tests/integration/
  ${PYTHON} -m pytest --log-cli-level="${TAVERN_LOG_LEVEL}" tests/integration/
}

run_static_analysis() {
  local exit_code=0
  echo -e "${BLUE}Running static analysis (ruff, black, bandit)...${NC}"

  echo -e "${BLUE}▶ Ruff check...${NC}"
  ${RUNNER:+${RUNNER} }ruff check . || exit_code=1

  echo -e "${BLUE}▶ Black format check...${NC}"
  ${RUNNER:+${RUNNER} }black --check . || exit_code=1

  echo -e "${BLUE}▶ Bandit security scan...${NC}"
  ${RUNNER:+${RUNNER} }bandit -c pyproject.toml -r . || exit_code=1

  return ${exit_code}
}

run_coverage() {
  echo -e "${BLUE}Running tests with code coverage...${NC}"
  ${PYTHON} -m pytest --cov=src --cov-report=term-missing tests/unit
}

print_help() {
  echo "Usage: ./run_tests.sh [OPTION]"
  echo ""
  echo "Options:"
  echo "  (no args)  Run all tests (unit + integration)"
  echo "  -u         Run unit tests only"
  echo "  -i         Run integration tests only"
  echo "  -s         Run static analysis only (ruff, black, bandit)"
  echo "  -c         Run unit tests with code coverage report"
  echo "  -a         Run complete test suite (unit, integration, and static analysis)"
  echo "  -h         Show this help message"
}

# --- CLI Option Parsing ---
while getopts ":uicas h" option; do
  case $option in
    u)
      run_unit_tests
      exit 0
      ;;
    i)
      run_integration_tests
      exit 0
      ;;
    s)
      run_static_analysis
      exit $?
      ;;
    c)
      run_coverage
      exit $?
      ;;
    a)
      overall_status=0
      run_unit_tests || overall_status=1
      run_integration_tests || overall_status=1
      run_static_analysis || overall_status=1
      if [ ${overall_status} -eq 0 ]; then
        echo -e "${GREEN}✓ All checks and tests passed successfully!${NC}"
      else
        echo -e "${RED}✗ One or more checks/tests failed.${NC}"
      fi
      exit ${overall_status}
      ;;
    h|\?)
      print_help
      exit 0
      ;;
  esac
done

# Default: run unit + integration tests
run_unit_tests
run_integration_tests
