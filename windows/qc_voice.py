"""Microphone recording without PyAudio.

PyAudio has no prebuilt Windows wheel for newer Python versions (pip then needs a C++ compiler).
`sounddevice` ships a prebuilt PortAudio, so `py -m pip install sounddevice` just works.
record() is plain Python so it can be tested without a microphone.
"""
import math
from array import array
from collections import deque

RATE = 16000
BLOCK = 1024


def rms(block):
    s = array("h")
    s.frombytes(block)
    return math.sqrt(sum(x * x for x in s) / len(s)) if s else 0.0


def record(read_block, max_seconds=30, silence_seconds=1.5, start_timeout=6,
           rate=RATE, block=BLOCK):
    """read_block() -> bytes of 16-bit mono PCM. Returns the PCM of one spoken phrase:
    starts when the level rises above the room noise, stops after `silence_seconds` of quiet.
    Raises TimeoutError if nothing is said within `start_timeout` seconds."""
    per = block / rate
    calib = [rms(read_block()) for _ in range(5)]            # measure room noise
    threshold = max(400.0, 3 * sum(calib) / len(calib))
    pre = deque(maxlen=3)                                    # keep a little audio before speech starts
    frames, started, quiet, elapsed = [], False, 0.0, 0.0
    while elapsed < max_seconds:
        data = read_block()
        elapsed += per
        loud = rms(data) >= threshold
        if not started:
            if loud:
                started = True
                frames.extend(pre)
                frames.append(data)
            else:
                pre.append(data)
                if elapsed >= start_timeout:
                    raise TimeoutError("No speech heard")
        else:
            frames.append(data)
            quiet = 0.0 if loud else quiet + per
            if quiet >= silence_seconds:
                break
    return b"".join(frames)


def open_mic(rate=RATE, block=BLOCK):
    """Returns (stream, read_block). Caller must stop() and close() the stream."""
    import sounddevice as sd
    stream = sd.RawInputStream(samplerate=rate, channels=1, dtype="int16", blocksize=block)
    stream.start()

    def read_block():
        data, _overflowed = stream.read(block)
        return bytes(data)
    return stream, read_block
