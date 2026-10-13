"""Play a whole race in a pseudo-terminal: typing, a typo and its fix, the
word-clearing keys, the results screen, resizing it, and quitting."""
import csv
import os
import select
import signal
import struct
import sys
import tempfile
import time
import unittest

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


@unittest.skipIf(sys.platform == "win32", "needs a pty")
class Race(unittest.TestCase):
    def test_full_race(self):
        import fcntl
        import pty
        import termios

        data = tempfile.mkdtemp()
        pid, fd = pty.fork()
        if pid == 0:                      # child: run one race on a fixed quote
            try:
                os.environ["TERM"] = "xterm-256color"
                os.environ["XDG_DATA_HOME"] = data
                fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 90, 0, 0))
                sys.path.insert(0, SRC)
                import curses
                import importlib
                from typerace import app
                app = importlib.reload(app)   # pick up XDG_DATA_HOME if another test imported it first
                curses.wrapper(app.main, app.Picker([("t1", "hi there friend", "Tester")]))
            finally:
                os._exit(0)

        out = bytearray()

        def pump(t=0.3):
            end = time.time() + t
            while time.time() < end:
                r, _, _ = select.select([fd], [], [], 0.05)
                if r:
                    try:
                        out.extend(os.read(fd, 65536))
                    except OSError:
                        return

        def typ(text):
            for ch in text:
                os.write(fd, ch.encode())
                pump(0.04)

        pump(1)
        typ("hi ")
        typ("thx")
        os.write(fd, b"\x7f")             # backspace fixes the typo
        pump(0.1)
        typ("ere ")
        typ("frix")
        os.write(fd, b"\x08")             # ctrl+backspace clears the word
        pump(0.1)
        typ("fr")
        os.write(fd, b"\x1b\x7f")         # alt+backspace clears it too
        pump(0.2)
        typ("friend")
        pump(0.8)
        self.assertIn("race results", out.decode(errors="ignore"))

        before = len(out)                 # a window manager resizing the window
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 60, 0, 0))
        os.kill(pid, signal.SIGWINCH)
        pump(0.6)
        self.assertGreater(len(out), before, "results screen should redraw on resize")

        os.write(fd, b"q")
        pump(0.6)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(status, 0)

        with open(os.path.join(data, "typerace", "history.csv")) as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quote_by"], "Tester")
        self.assertAlmostEqual(float(rows[0]["accuracy"]), 100 * 20 / 22, places=1)   # 2 typos in 22 keys


if __name__ == "__main__":
    unittest.main()
