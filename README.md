# pitwall
Assorted things for examining live race data from livetiming.formula1.com

## capture.py
Connects to the WebSocket timing service and writes all timing-related messages to stdout, along with their read timestamp.

Example usage:
```shell
python -u ./capture.py | tee data/2024_belgium_gp_race.txt
```

