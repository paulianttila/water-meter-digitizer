#!/usr/bin/env bash

set -e

# --- Configuration & Defaults ---
TAVERN_LOG_LEVEL=${TAVERN_LOG_LEVEL:-INFO}
PWD=$(pwd)
AUTO_TEMP_CONFIG=""
if [ -z "${CONFIG_FILE}" ]; then
  if [ -f "/config/config.ini" ]; then
    export CONFIG_FILE="/config/config.ini"
  elif [ -f "${PWD}/config/config.ini" ]; then
    if [ ! -d "/config" ]; then
      AUTO_TEMP_CONFIG="${PWD}/image_tmp/test_config.ini"
      mkdir -p "${PWD}/image_tmp"
      sed -e "s|^ConfigDir.*=.*|ConfigDir = ${PWD}/config|g" \
          -e "s|file:///config/|file://${PWD}/config/|g" \
          "${PWD}/config/config.ini" > "${AUTO_TEMP_CONFIG}"
      export CONFIG_FILE="${AUTO_TEMP_CONFIG}"
    else
      export CONFIG_FILE="${PWD}/config/config.ini"
    fi
  fi
fi

# --- ANSI Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- Runner Validation ---
if ! command -v uv >/dev/null 2>&1; then
  echo -e "${RED}Error: 'uv' is required to run tests. Please install uv: https://docs.astral.sh/uv/${NC}"
  exit 1
fi
PYTHON="uv run --no-sync python"

TEST_APP_PID=
MQTT_BROKER_PID=

# --- Process Management & Cleanup ---
stop_test_app() {
  if [ -n "${TEST_APP_PID}" ] && kill -0 "${TEST_APP_PID}" 2>/dev/null; then
    echo -e "${YELLOW}Stopping test app (PID=${TEST_APP_PID})...${NC}"
    kill "${TEST_APP_PID}" 2>/dev/null || kill -9 "${TEST_APP_PID}" 2>/dev/null
    wait "${TEST_APP_PID}" 2>/dev/null || true
    TEST_APP_PID=
  fi
}

stop_mqtt_broker() {
  if [ -n "${MQTT_BROKER_PID}" ] && kill -0 "${MQTT_BROKER_PID}" 2>/dev/null; then
    echo -e "${YELLOW}Stopping MQTT broker (PID=${MQTT_BROKER_PID})...${NC}"
    kill "${MQTT_BROKER_PID}" 2>/dev/null || kill -9 "${MQTT_BROKER_PID}" 2>/dev/null
    wait "${MQTT_BROKER_PID}" 2>/dev/null || true
    MQTT_BROKER_PID=
  fi
}

clean_up() {
  stop_test_app
  stop_mqtt_broker
  if [ -n "${AUTO_TEMP_CONFIG}" ] && [ -f "${AUTO_TEMP_CONFIG}" ]; then
    rm -f "${AUTO_TEMP_CONFIG}"
  fi
}
trap clean_up EXIT INT TERM

start_mqtt_broker() {
  echo -e "${BLUE}Starting MQTT test broker...${NC}"
  local mosquitto_bin=""
  if command -v mosquitto >/dev/null 2>&1; then
    mosquitto_bin="mosquitto"
  elif [ -x "/opt/homebrew/sbin/mosquitto" ]; then
    mosquitto_bin="/opt/homebrew/sbin/mosquitto"
  elif [ -x "/usr/local/sbin/mosquitto" ]; then
    mosquitto_bin="/usr/local/sbin/mosquitto"
  fi

  if [ -n "${mosquitto_bin}" ]; then
    echo -e "${BLUE}Using Mosquitto broker: ${mosquitto_bin}${NC}"
    "${mosquitto_bin}" -c "${PWD}/tests/integration/mosquitto.conf" &
    MQTT_BROKER_PID=$!
  else
    echo -e "${BLUE}Mosquitto not found, using Python amqtt broker...${NC}"
    ${PYTHON} tests/integration/mqtt_broker.py &
    MQTT_BROKER_PID=$!
  fi
  echo -e "${BLUE}MQTT broker PID: ${MQTT_BROKER_PID}${NC}"

  echo -e "${BLUE}Waiting for MQTT broker to become ready on port 1883...${NC}"
  for i in {1..20}; do
    if ! kill -0 "${MQTT_BROKER_PID}" 2>/dev/null; then
      echo -e "${RED}Error: MQTT broker exited prematurely!${NC}"
      exit 1
    fi
    if ${PYTHON} -c "import socket; s = socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1', 1883)); s.close()" 2>/dev/null; then
      echo -e "${GREEN}✓ MQTT broker is ready!${NC}"
      return 0
    fi
    sleep 0.25
  done
  echo -e "${RED}Error: MQTT broker did not start on port 1883 within 5s${NC}"
  exit 1
}

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

run_ui_tests() {
  echo -e "${BLUE}Running Web UI integration tests (Playwright)...${NC}"
  ${PYTHON} -m pytest tests/integration/ui/ -v
}

run_integration_tests() {
  start_mqtt_broker
  start_test_app
  echo -e "${BLUE}Running Tavern integration tests...${NC}"
  export PYTHONPATH=${PYTHONPATH}:${PWD}/tests/integration/
  local status=0
  ${PYTHON} -m pytest --log-cli-level="${TAVERN_LOG_LEVEL}" -m "not ui" tests/integration/ || status=$?
  stop_test_app
  stop_mqtt_broker
  return ${status}
}

run_static_analysis() {
  local exit_code=0
  echo -e "${BLUE}Running static analysis (ruff, black, bandit)...${NC}"

  echo -e "${BLUE}▶ Ruff check...${NC}"
  ${PYTHON} -m ruff check . || exit_code=1

  echo -e "${BLUE}▶ Black format check...${NC}"
  ${PYTHON} -m black --check . || exit_code=1

  echo -e "${BLUE}▶ Bandit security scan...${NC}"
  ${PYTHON} -m bandit -c pyproject.toml -r . || exit_code=1

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
  echo "  (no args)               Run all tests (unit + UI + Tavern integration)"
  echo "  -u, --unit              Run unit tests only"
  echo "  -w, --ui, --web-ui      Run Web UI tests only (Playwright)"
  echo "  -i, --integration       Run Tavern integration tests only"
  echo "  -s, --static            Run static analysis only (ruff, black, bandit)"
  echo "  -c, --coverage          Run unit tests with code coverage report"
  echo "  -a, --all               Run complete test suite (unit, UI, Tavern integration, and static analysis)"
  echo "  -h, --help              Show this help message"
}

# --- CLI Option Parsing ---
if [ $# -eq 0 ]; then
  # Default: run unit + UI + Tavern integration tests
  run_unit_tests
  run_ui_tests
  run_integration_tests
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u|--unit)
      run_unit_tests
      shift
      ;;
    -w|--ui|--web-ui)
      run_ui_tests
      shift
      ;;
    -i|--integration|--tavern)
      run_integration_tests
      shift
      ;;
    -s|--static)
      run_static_analysis
      shift
      ;;
    -c|--coverage)
      run_coverage
      shift
      ;;
    -a|--all)
      overall_status=0
      run_unit_tests || overall_status=1
      run_ui_tests || overall_status=1
      run_integration_tests || overall_status=1
      run_static_analysis || overall_status=1
      if [ ${overall_status} -eq 0 ]; then
        echo -e "${GREEN}✓ All checks and tests passed successfully!${NC}"
      else
        echo -e "${RED}✗ One or more checks/tests failed.${NC}"
      fi
      exit ${overall_status}
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      print_help
      exit 1
      ;;
  esac
done
