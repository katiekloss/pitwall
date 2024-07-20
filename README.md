# pitwall
Assorted things for examining live race data from livetiming.formula1.com

## telnet.py
Mostly for debugging. Connects to the timing service and writes all timing-related messages to stdout.

Example usage:
```shell
python -u ./record.py | tee timingdump.txt
```

