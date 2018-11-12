#! /bin/bash
IDS=()

finish() {
  kill $(jobs -p)
  rm .pytor_lock
  exit;
}

trap finish SIGHUP SIGINT SIGTERM

echo "Setting up Directory"
python src/common/mini_pytor/directory.py &
IDS+=($!)

sleep 3

echo "Setting up Relays"
for relay in a b c; do
  python src/common/mini_pytor/relay.py $relay &
  IDS+=($!)
done

echo "Quit to kill all processes"
touch .pytor_lock

while true
do
  sleep 1
done
