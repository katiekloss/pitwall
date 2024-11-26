# pitwall
Assorted things for examining live race data from livetiming.formula1.com, which is the event stream that powers the official "Live Timing" app on formula1.com and the mobile apps.

## capture.py
Connects to the WebSocket timing service and writes all timing-related messages to a file, along with their read timestamp.
```shell
pipenv run ./capture.py -o data/2024_belgium_gp_race.txt
```

## replay.py
Replays the output of `capture.py` at (roughly) the same speed as the original event stream, and optionally outputs to a FIFO.
```shell
pipenv run ./replay.py -i data/2024_belgium_gp_race.txt -o replay.fifo -x 20
```

`-x 5` replays the stream at 5 times the original speed.

## watch.py
Debug script which processes the event stream in the context of a track session.
```shell
pipenv run ./watch.py -i replay.fifo
```
or, to read the original file as fast as possible:
```shell
pipenv run ./watch.py -i data/2024_belgium_gp_race.txt
```
