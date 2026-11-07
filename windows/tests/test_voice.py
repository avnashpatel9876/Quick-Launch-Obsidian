import sys, unittest
from array import array
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import qc_voice as v


def blk(level):
    return array("h", [level, -level] * (v.BLOCK // 2)).tobytes()


def feeder(levels):
    it = iter(levels)
    return lambda: blk(next(it))


class Record(unittest.TestCase):
    def test_rms(self):
        self.assertAlmostEqual(v.rms(blk(1000)), 1000.0)
        self.assertEqual(v.rms(b""), 0.0)

    def test_stops_after_silence(self):
        levels = [10] * 5 + [10] * 4 + [3000] * 10 + [10] * 60
        out = v.record(feeder(levels))
        n = len(out) // (v.BLOCK * 2)
        self.assertGreater(n, 10)                  # includes the speech
        self.assertLess(n, 10 + 3 + 26)            # pre-roll + speech + ~1.5 s tail, not the whole feed
        self.assertTrue(any(abs(x) > 2000 for x in array("h", out)))

    def test_no_speech_times_out(self):
        with self.assertRaises(TimeoutError):
            v.record(feeder([10] * 500))

    def test_max_seconds_caps_long_speech(self):
        out = v.record(feeder([10] * 5 + [3000] * 1000), max_seconds=2)
        self.assertLess(len(out) / 2 / v.RATE, 2.2)


if __name__ == "__main__":
    unittest.main()
