"""typerace: TypeRacer-style typing races in the terminal.

Type a quote word by word, as fast as you can. The input box only clears once a
word (and its space) is right; mistakes show red and must be fixed.

Keys: Ctrl+Backspace / Ctrl+W / Alt+Backspace = clear the word,
      Tab = new quote, Esc = quit (q also quits from the results screen).

Results, and which quotes you've already done, are kept in
$XDG_DATA_HOME/typerace (default ~/.local/share/typerace).
"""
import argparse
import csv
import curses
import datetime as dt
import json
import os
import random
import sys
import textwrap
import time

from . import __version__

DATA = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "typerace")
HISTORY = os.path.join(DATA, "history.csv")
SEEN_FILE = os.path.join(DATA, "seen.json")
# length groups (characters) and how often each comes up in a mixed race
LENGTHS = {"short": (0, 100, 25), "medium": (101, 300, 45), "long": (301, 600, 25), "verylong": (601, 99999, 5)}
# the car on the race lane; set TYPERACE_NERD_FONT=1 for a Nerd Font car icon
CAR = "\U000F010B" if os.environ.get("TYPERACE_NERD_FONT") else "\u25b6"

# fallback if the bundled quotes can't be read: (passage, "Author, Title"),
# all public domain
QUOTES = [
    ("It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, "
     "it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of "
     "Darkness, it was the spring of hope, it was the winter of despair.", "Charles Dickens, A Tale of Two Cities"),
    ("It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of "
     "a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, "
     "this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful "
     "property of some one or other of their daughters.", "Jane Austen, Pride and Prejudice"),
    ("Call me Ishmael. Some years ago - never mind how long precisely - having little or no money in my purse, and "
     "nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of "
     "the world. It is a way I have of driving off the spleen and regulating the circulation.",
     "Herman Melville, Moby-Dick"),
    ("I went to the woods because I wished to live deliberately, to front only the essential facts of life, and see "
     "if I could not learn what it had to teach, and not, when I came to die, discover that I had not lived. I did "
     "not wish to live what was not life, living is so dear; nor did I wish to practise resignation, unless it was "
     "quite necessary.", "Henry David Thoreau, Walden"),
    ("Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in "
     "Liberty, and dedicated to the proposition that all men are created equal. Now we are engaged in a great civil "
     "war, testing whether that nation, or any nation so conceived and so dedicated, can long endure.",
     "Abraham Lincoln, the Gettysburg Address"),
    ("It is interesting to contemplate an entangled bank, clothed with many plants of many kinds, with birds "
     "singing on the bushes, with various insects flitting about, and with worms crawling through the damp earth, "
     "and to reflect that these elaborately constructed forms, so different from each other, and dependent on each "
     "other in so complex a manner, have all been produced by laws acting around us.",
     "Charles Darwin, On the Origin of Species"),
    ("I consider that a man's brain originally is like a little empty attic, and you have to stock it with such "
     "furniture as you choose. A fool takes in all the lumber of every sort that he comes across, so that the "
     "knowledge which might be useful to him gets crowded out, or at best is jumbled up with a lot of other things "
     "so that he has a difficulty in laying his hands upon it.", "Arthur Conan Doyle, A Study in Scarlet"),
    ("Tom said to himself that it was not such a hollow world, after all. He had discovered a great law of human "
     "action, without knowing it - namely, that in order to make a man or a boy covet a thing, it is only necessary "
     "to make the thing difficult to attain.", "Mark Twain, The Adventures of Tom Sawyer"),
    ("Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do: once "
     "or twice she had peeped into the book her sister was reading, but it had no pictures or conversations in it, "
     "'and what is the use of a book,' thought Alice 'without pictures or conversations?'",
     "Lewis Carroll, Alice's Adventures in Wonderland"),
    ("Climb the mountains and get their good tidings. Nature's peace will flow into you as sunshine flows into "
     "trees. The winds will blow their own freshness into you, and the storms their energy, while cares will drop "
     "off like autumn leaves.", "John Muir, Our National Parks"),
    ("Trust thyself: every heart vibrates to that iron string. Accept the place the divine providence has found for "
     "you, the society of your contemporaries, the connection of events. Great men have always done so, and "
     "confided themselves childlike to the genius of their age.", "Ralph Waldo Emerson, Self-Reliance"),
    ("You will rejoice to hear that no disaster has accompanied the commencement of an enterprise which you have "
     "regarded with such evil forebodings. I arrived here yesterday, and my first task is to assure my dear sister "
     "of my welfare and increasing confidence in the success of my undertaking.", "Mary Shelley, Frankenstein"),
    ("Buck did not read the newspapers, or he would have known that trouble was brewing, not alone for himself, but "
     "for every tide-water dog, strong of muscle and with warm, long hair, from Puget Sound to San Diego.",
     "Jack London, The Call of the Wild"),
    ("Marley was dead: to begin with. There is no doubt whatever about that. The register of his burial was signed "
     "by the clergyman, the clerk, the undertaker, and the chief mourner. Scrooge signed it: and Scrooge's name was "
     "good upon 'Change, for anything he chose to put his hand to.", "Charles Dickens, A Christmas Carol"),
    ("In my younger and more vulnerable years my father gave me some advice that I've been turning over in my mind "
     "ever since. 'Whenever you feel like criticizing any one,' he told me, 'just remember that all the people in "
     "this world haven't had the advantages that you've had.'", "F. Scott Fitzgerald, The Great Gatsby"),
    ("Happy families are all alike; every unhappy family is unhappy in its own way. Everything was in confusion in "
     "the Oblonskys' house. The wife had discovered that the husband was carrying on an intrigue with a French girl, "
     "who had been a governess in their family, and she had announced to her husband that she could not go on "
     "living in the same house with him.", "Leo Tolstoy, Anna Karenina"),
    ("There was no possibility of taking a walk that day. We had been wandering, indeed, in the leafless shrubbery "
     "an hour in the morning; but since dinner (Mrs. Reed, when there was no company, dined early) the cold winter "
     "wind had brought with it clouds so sombre, and a rain so penetrating, that further out-door exercise was now "
     "out of the question.", "Charlotte Bronte, Jane Eyre"),
    ("It is not the critic who counts; not the man who points out how the strong man stumbles, or where the doer of "
     "deeds could have done them better. The credit belongs to the man who is actually in the arena, whose face is "
     "marred by dust and sweat and blood; who strives valiantly; who errs, who comes short again and again.",
     "Theodore Roosevelt, Citizenship in a Republic"),
    ("No one would have believed in the last years of the nineteenth century that this world was being watched "
     "keenly and closely by intelligences greater than man's and yet as mortal as his own; that as men busied "
     "themselves about their various concerns they were scrutinised and studied, perhaps almost as narrowly as a man "
     "with a microscope might scrutinise the transient creatures that swarm and multiply in a drop of water.",
     "H. G. Wells, The War of the Worlds"),
    ("The artist is the creator of beautiful things. To reveal art and conceal the artist is art's aim. The critic "
     "is he who can translate into another manner or a new material his impression of beautiful things.",
     "Oscar Wilde, The Picture of Dorian Gray"),
    ("Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; "
     "whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every "
     "funeral I meet; then, I account it high time to get to sea as soon as I can.", "Herman Melville, Moby-Dick"),
]

def typable(text):
    """Plain keyboard version of a quote, or None if it still has odd characters."""
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2014", " - "),
                 ("\u2013", "-"), ("\u2026", "..."), ("\u00a0", " ")):
        text = text.replace(a, b)
    text = " ".join(text.split())
    return text if text.isascii() and text.isprintable() and len(text) >= 10 else None


def all_quotes():
    """[(id, text, source)]: the bundled collection, else the built-ins."""
    try:
        from importlib.resources import files
        return [tuple(q) for q in json.loads(files("typerace").joinpath("quotes.json").read_text("utf-8"))]
    except Exception:
        return [(f"b{i}", t, src) for i, (t, src) in enumerate(QUOTES)]


class Picker:
    """Random quotes of a random length, never repeating one until every quote
    of that length has been done."""

    def __init__(self, quotes, only=None):
        self.groups = {name: [q for q in quotes if lo <= len(q[1]) <= hi]
                       for name, (lo, hi, _) in LENGTHS.items() if only in (None, name)}
        self.groups = {k: v for k, v in self.groups.items() if v}
        try:
            self.seen = set(json.load(open(SEEN_FILE)))
        except (OSError, ValueError):
            self.seen = set()

    def next(self):
        names = list(self.groups)
        name = random.choices(names, [LENGTHS[n][2] for n in names])[0]
        group = self.groups[name]
        fresh = [q for q in group if q[0] not in self.seen]
        if not fresh:                     # done them all: start this length over
            self.seen -= {q[0] for q in group}
            fresh = group
        q = random.choice(fresh)
        self.seen.add(q[0])
        os.makedirs(DATA, exist_ok=True)
        with open(SEEN_FILE, "w") as f:
            json.dump(sorted(self.seen), f)
        return q[1], q[2] or "unknown"


# colour pairs
OK, BAD, BADBG, DIM, ACC, TXT, CUR = range(1, 8)


def wpm(chars, secs):
    return chars / 5 / (secs / 60) if secs > 0 else 0.0


def save(speed, acc, secs, source):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    new = not os.path.exists(HISTORY)
    with open(HISTORY, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "wpm", "accuracy", "seconds", "quote_by"])
        w.writerow([dt.datetime.now().isoformat(timespec="seconds"), f"{speed:.1f}", f"{acc:.1f}", f"{secs:.1f}", source])


def history():
    try:
        with open(HISTORY) as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def put(scr, y, x, s, attr=0):
    try:
        scr.addstr(y, x, s, attr)
    except curses.error:
        pass


def box(scr, y, x, h, w, attr):
    put(scr, y, x, "╭" + "─" * (w - 2) + "╮", attr)
    for i in range(1, h - 1):
        put(scr, y + i, x, "│", attr)
        put(scr, y + i, x + w - 1, "│", attr)
    put(scr, y + h - 1, x, "╰" + "─" * (w - 2) + "╯", attr)


def read_key(scr):
    """A key, with Alt+Backspace folded into 'delete word'."""
    k = scr.get_wch()
    if k == "\x1b":
        scr.nodelay(True)
        try:
            nxt = scr.get_wch()
        except curses.error:
            nxt = None
        scr.nodelay(False)
        if nxt in ("\x7f", curses.KEY_BACKSPACE, "\x08"):
            return "DELWORD"
        if nxt is not None:
            return None                   # some other escape sequence: ignore
        return "ESC"
    if k in ("\x08", "\x17"):             # Ctrl+Backspace, Ctrl+W
        return "DELWORD"
    if k == curses.KEY_BACKSPACE:
        # curses turns the terminal's "backspace" code into KEY_BACKSPACE. Where
        # that code is ^H (macOS terminfo), the Backspace key itself sends DEL
        # and ^H means Ctrl+Backspace.
        return "DELWORD" if curses.tigetstr("kbs") == b"\x08" else "BACK"
    if k == "\x7f":
        return "BACK"
    return k


def race(scr, text, source):
    """One race. Returns (wpm, accuracy, seconds), 'next' (Tab) or None (Esc)."""
    words = text.split(" ")
    targets = [w + " " for w in words[:-1]] + [words[-1]]
    starts = [sum(len(t) for t in targets[:i]) for i in range(len(targets))]
    wi, cur = 0, ""                       # current word index, input box contents
    start = None
    keystrokes = errors = 0
    log, typos = [(0.0, 0)], []           # (seconds, characters done) per word; typo times
    scr.timeout(200)                      # redraw a few times a second for the live WPM
    while True:
        h, w = scr.getmaxyx()
        width = max(30, min(w - 4, 76))
        left = max(0, (w - width) // 2)
        inner = width - 4
        lines = textwrap.wrap(text, inner) or [text]
        top = max(0, (h - (len(lines) + 13)) // 2)

        target = targets[wi] if wi < len(targets) else ""
        good = 0                          # correct prefix of the input box
        while good < len(cur) and good < len(target) and cur[good] == target[good]:
            good += 1
        wrong = len(cur) > good
        done_chars = starts[wi] + good if wi < len(targets) else len(text)
        elapsed = time.time() - start if start else 0
        speed = wpm(done_chars, elapsed)
        acc = 100 * (keystrokes - errors) / keystrokes if keystrokes else 100

        scr.erase()
        # --- race lane --------------------------------------------------------------
        box(scr, top, left, 4, width, curses.color_pair(DIM))
        put(scr, top, left + 2, " race ", curses.color_pair(DIM))
        lane = inner - 12
        pos = int(lane * done_chars / len(text))
        put(scr, top + 1, left + 2, "you", curses.color_pair(TXT) | curses.A_BOLD)
        put(scr, top + 2, left + 2, "┄" * lane, curses.color_pair(DIM))
        put(scr, top + 2, left + 2 + lane, "┃", curses.color_pair(DIM))
        put(scr, top + 2, left + 2 + min(pos, lane - 1), CAR + " ", curses.color_pair(ACC) | curses.A_BOLD)
        put(scr, top + 2, left + width - 10, f"{speed:4.0f} wpm", curses.color_pair(ACC) | curses.A_BOLD)

        # --- passage: done words green, current word underlined, mistakes red -------
        ptop = top + 5
        box(scr, ptop, left, len(lines) + 2, width, curses.color_pair(DIM))
        i = 0
        cur_start = starts[wi] if wi < len(targets) else len(text)
        cur_end = cur_start + len(words[wi]) if wi < len(words) else cur_start
        for row, line in enumerate(lines):
            for col, ch in enumerate(line):
                # textwrap drops the spaces it wraps at; keep i in step with text
                while i < len(text) and text[i] != ch:
                    i += 1
                if i < cur_start:
                    attr = curses.color_pair(OK)
                elif i < cur_start + good:
                    attr = curses.color_pair(OK) | curses.A_UNDERLINE
                elif i < cur_start + len(cur):
                    attr = curses.color_pair(BADBG)
                elif i < cur_end:
                    attr = curses.color_pair(TXT) | curses.A_UNDERLINE
                else:
                    attr = curses.color_pair(TXT)
                put(scr, ptop + 1 + row, left + 2 + col, ch, attr)
                i += 1

        # --- input box ---------------------------------------------------------------
        itop = ptop + len(lines) + 3
        box(scr, itop, left, 3, width, curses.color_pair(BAD if wrong else ACC))
        shown = cur[-(inner - 1):]
        put(scr, itop + 1, left + 2, shown, curses.color_pair(BAD if wrong else TXT))
        put(scr, itop + 1, left + 2 + len(shown), " ", curses.color_pair(CUR) | curses.A_REVERSE)
        if start is None:
            put(scr, itop + 1, left + 4, "type the text above when you're ready", curses.color_pair(DIM))
        put(scr, itop + 3, left + 2, f"{acc:.0f}% accuracy · {elapsed:.0f}s", curses.color_pair(DIM))
        hint = "ctrl+backspace clear word · tab new text · esc quit"
        put(scr, itop + 3, left + width - 2 - len(hint), hint, curses.color_pair(DIM))
        scr.refresh()

        if wi == len(targets):
            return speed, acc, elapsed, log, typos

        try:
            key = read_key(scr)
        except curses.error:
            continue                      # timeout: just redraw
        if key is None:
            continue
        if key == "ESC":
            return None
        if key == "\t":
            return "next"
        if key == "BACK":
            cur = cur[:-1]
        elif key == "DELWORD":
            cur = ""
        elif isinstance(key, str) and key.isprintable() and len(cur) < len(target) + 12:
            if start is None:
                start = time.time()
            keystrokes += 1
            cur += key
            if not target.startswith(cur):
                errors += 1
                typos.append(time.time() - start)
            if cur == target:             # word done: lock it in and clear the box
                log.append((time.time() - start, starts[wi] + len(target)))
                wi += 1
                cur = ""


def chars_at(log, t):
    """Characters typed by time t, interpolated between finished words."""
    for (t0, c0), (t1, c1) in zip(log, log[1:]):
        if t <= t1:
            return c0 + (c1 - c0) * (t - t0) / (t1 - t0) if t1 > t0 else c1
    return log[-1][1]


def speed_curve(log, secs, n):
    """n samples of speed (wpm) over the race, each averaged over a short window."""
    win = max(2.0, secs / 12)
    out = []
    for i in range(n):
        t = secs * (i + 1) / n
        w = min(win, t)
        out.append((chars_at(log, t) - chars_at(log, t - w)) / 5 / (w / 60) if w > 0 else 0)
    return out


def braille_plot(scr, y, x, rows, cols, values, vmax, attr):
    """Line chart of `values` (2 per column) in braille dots."""
    bits = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
    cells = {}
    h = rows * 4 - 1
    prev = None
    for i, v in enumerate(values[:cols * 2]):
        dy = round((1 - min(v, vmax) / vmax) * h) if vmax else h
        lo, hi = (dy, dy) if prev is None else (min(prev, dy), max(prev, dy))
        for yy in range(lo, hi + 1):          # join to the previous point
            key = (yy // 4, i // 2)
            cells[key] = cells.get(key, 0) | bits[i % 2][yy % 4]
        prev = dy
    for (r, c), b in cells.items():
        put(scr, y + r, x + c, chr(0x2800 + b), attr)


def best_stretch(log, secs):
    """Fastest sustained speed: the best wpm over any stretch of at least 3 s
    (or 15% of the race), so two words finished at nearly the same moment
    don't count as a burst."""
    span = min(secs, max(3.0, secs * 0.15))
    best = 0.0
    for i, (t0, c0) in enumerate(log):
        for t1, c1 in log[i + 1:]:
            if t1 - t0 >= span - 1e-9:
                best = max(best, (c1 - c0) / 5 / ((t1 - t0) / 60))
                break
    return best, span


AOS = (5, 12, 25, 50, 100)


def ao(values, n):
    """Speedcubing-style average of n (cstimer convention): drop the fastest
    and slowest 5% (rounded up; 1 each for ao5/ao12, 2 for ao25, 3 for ao50,
    5 for ao100) and average the rest. None if there aren't n results."""
    if len(values) < n:
        return None
    k = -(-n * 5 // 100)
    kept = sorted(values[-n:])[k:n - k]
    return sum(kept) / len(kept)


def best_ao(values, n):
    found = [a for i in range(n, len(values) + 1) if (a := ao(values[:i], n)) is not None]
    return max(found, default=None)


def results(scr, speed, acc, secs, log, typos, source):
    past = history()
    best = max((float(r["wpm"]) for r in past), default=0)
    save(speed, acc, secs, source)
    speeds = [float(r["wpm"]) for r in past] + [speed]

    def draw():
        # drawn again whenever the window is resized (e.g. a new i3 tab or split)
        h, w = scr.getmaxyx()
        width = min(w - 4, 76)
        left = max(0, (w - width) // 2)
        chart_rows = max(0, min(8, h - 29))
        height = 18 + (chart_rows + 5 if chart_rows >= 3 else 0)
        top = max(0, (h - height - 2) // 2)
        scr.erase()
        box(scr, top, left, height, width, curses.color_pair(ACC))
        put(scr, top, left + 2, " race results ", curses.color_pair(ACC) | curses.A_BOLD)

        # pace through the race: speed in each quarter of the time
        q = [(chars_at(log, secs * (i + 1) / 4) - chars_at(log, secs * i / 4)) / 5 / (secs / 4 / 60) for i in range(4)]
        curve = speed_curve(log, secs, max(8, (width - 12) * 2))
        peak, span = best_stretch(log, secs)
        change = q[3] - q[0]
        rows = [
            ("speed", f"{speed:.0f} wpm", curses.color_pair(ACC) | curses.A_BOLD),
            ("accuracy", f"{acc:.1f}%  ({len(typos)} typo{'s' if len(typos) != 1 else ''})", curses.color_pair(TXT)),
            ("time", f"{secs:.1f}s", curses.color_pair(TXT)),
            ("peak", f"{peak:.0f} wpm  (best {span:.0f}s stretch)", curses.color_pair(TXT)),
            ("pace", f"{q[0]:.0f} > {(q[1] + q[2]) / 2:.0f} > {q[3]:.0f} wpm  ({'+' if change >= 0 else ''}{change:.0f} start to finish)",
             curses.color_pair(OK if change >= 0 else BAD)),
        ]
        for i, (k, v, attr) in enumerate(rows):
            put(scr, top + 2 + i, left + 4, f"{k:<10}", curses.color_pair(DIM))
            put(scr, top + 2 + i, left + 16, v[:width - 20], attr)
        if speed > best:
            put(scr, top + 8, left + 4, "new personal best!", curses.color_pair(OK) | curses.A_BOLD)
        else:
            put(scr, top + 8, left + 4, f"personal best {best:.0f} wpm", curses.color_pair(DIM))

        # averages, speedcubing style: current (ending with this race) and best ever
        col = 8
        put(scr, top + 10, left + 16, "single".rjust(col - 2) + "".join(f"ao{n}".rjust(col) for n in AOS),
            curses.color_pair(DIM))
        put(scr, top + 11, left + 4, "current", curses.color_pair(DIM))
        put(scr, top + 12, left + 4, "best", curses.color_pair(DIM))
        put(scr, top + 11, left + 16, f"{speed:.0f}".rjust(col - 2), curses.color_pair(TXT))
        put(scr, top + 12, left + 16, f"{max(speeds):.0f}".rjust(col - 2), curses.color_pair(TXT))
        for i, n in enumerate(AOS):
            x = left + 16 + col - 2 + i * col
            cur, prev_best, best_n = ao(speeds, n), best_ao(speeds[:-1], n), best_ao(speeds, n)
            new_best = cur is not None and (prev_best is None or cur > prev_best)
            put(scr, top + 11, x, (f"{cur:.1f}" if cur is not None else "-").rjust(col),
                curses.color_pair(OK) | curses.A_BOLD if new_best else curses.color_pair(TXT))
            put(scr, top + 12, x, (f"{best_n:.1f}" if best_n is not None else "-").rjust(col), curses.color_pair(TXT))

        # the last 12 races, newest first, cstimer style: the ones ao12 drops in
        # brackets, this race highlighted
        last = speeds[-12:]
        drop = set()
        if len(last) == 12:
            order = sorted(range(12), key=lambda i: last[i])
            drop = {order[0], order[-1]}
        total = f"{len(speeds)} race{'s' if len(speeds) != 1 else ''} total"
        put(scr, top + 14, left + 4, f"last {len(last)} races", curses.color_pair(DIM))
        put(scr, top + 14, left + width - 4 - len(total), total, curses.color_pair(DIM))
        step = max(5, min(6, (width - 9) // 12))              # column spacing that fits 12
        for slot, i in enumerate(reversed(range(len(last)))):   # newest on the left
            v = last[i]
            text = f"({v:.0f})" if i in drop else f"{v:.0f}"
            attr = curses.color_pair(ACC) | curses.A_BOLD if i == len(last) - 1 else \
                curses.color_pair(DIM) if i in drop else curses.color_pair(TXT)
            x = left + 4 + slot * step
            if x + 6 <= left + width - 1:
                put(scr, top + 15, x + 5 - len(text) + (1 if i in drop else 0), text, attr)

        # chart: speed over the race, the final average as a dashed line, typos below
        if chart_rows >= 3:
            cy, cx = top + 17, left + 9
            cols = width - 12
            vmax = max(20, int(max(curve + [speed]) * 1.15 / 10 + 1) * 10)
            put(scr, cy, left + 2, "speed over the race", curses.color_pair(DIM))
            cy += 1
            avg_row = round((1 - speed / vmax) * (chart_rows * 4 - 1)) // 4
            for c in range(cols):
                put(scr, cy + avg_row, cx + c, "╌", curses.color_pair(DIM))
            braille_plot(scr, cy, cx, chart_rows, cols, curve, vmax, curses.color_pair(ACC))
            for r, label in ((0, vmax), (chart_rows // 2, vmax // 2), (chart_rows - 1, 0)):
                put(scr, cy + r, left + 2, f"{label:>5} ", curses.color_pair(DIM))
            put(scr, cy + chart_rows, cx, "└" + "─" * (cols - 1), curses.color_pair(DIM))
            for t in typos:                   # typo ticks along the time axis
                put(scr, cy + chart_rows, cx + min(cols - 1, int(t / secs * cols)), "▴",
                    curses.color_pair(BAD) | curses.A_BOLD)
            put(scr, cy + chart_rows + 1, cx, "0s", curses.color_pair(DIM))
            put(scr, cy + chart_rows + 1, cx + cols - len(f"{secs:.0f}s"), f"{secs:.0f}s", curses.color_pair(DIM))
            legend = "⠒ speed  ╌ average  ▴ typo"
            put(scr, cy + chart_rows + 1, cx + (cols - len(legend)) // 2, legend, curses.color_pair(DIM))

        put(scr, top + height - 1, left + 2, f" {source[:width - 8]} ", curses.color_pair(TXT) | curses.A_ITALIC)
        put(scr, top + height + 1, left + 2, "enter race again · q / esc quit", curses.color_pair(DIM))
        scr.refresh()
    scr.timeout(250)                      # wake up regularly so resizes are noticed
    draw()
    while True:
        try:
            k = read_key(scr)
        except curses.error:
            continue
        if k == curses.KEY_RESIZE:
            draw()
            continue
        if k in ("\n", "\t", " ", curses.KEY_ENTER):
            return True
        if k in ("ESC", "q", "Q"):
            return False


def main(scr, picker):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.set_escdelay(25)
    dim = 8 if curses.COLORS > 8 else curses.COLOR_WHITE
    curses.init_pair(OK, curses.COLOR_GREEN, -1)
    curses.init_pair(BAD, curses.COLOR_RED, -1)
    curses.init_pair(BADBG, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(DIM, dim, -1)
    curses.init_pair(ACC, curses.COLOR_CYAN, -1)
    curses.init_pair(TXT, curses.COLOR_WHITE, -1)
    curses.init_pair(CUR, curses.COLOR_CYAN, -1)
    while True:
        quote = picker.next()
        r = race(scr, *quote)
        if r is None:
            return
        if r == "next":
            continue
        if not results(scr, *r, quote[1]):
            return


def show_history():
    rows = history()
    if not rows:
        print("no races yet")
        return 0
    for r in rows[-15:]:
        print(f"{r['date'].replace('T', ' ')}  {float(r['wpm']):5.0f} wpm  {float(r['accuracy']):5.1f}%  {r['quote_by']}")
    speeds = [float(r["wpm"]) for r in rows]
    aos = "  ".join(f"ao{n} {a:.1f}" for n in AOS if (a := ao(speeds, n)) is not None)
    print(f"\n{len(rows)} races, best {max(speeds):.0f} wpm" + (f"  ·  {aos}" if aos else ""))
    return 0


def cli(argv=None):
    p = argparse.ArgumentParser(
        prog="typerace",
        description="TypeRacer-style typing races in the terminal.",
        epilog="keys: ctrl+backspace / ctrl+w clear the word, tab new quote, esc quit. "
               "Set TYPERACE_NERD_FONT=1 for a car icon if your terminal uses a Nerd Font.")
    p.add_argument("length", nargs="?", choices=list(LENGTHS),
                   help="only race quotes of this length (default: a mix)")
    p.add_argument("--history", action="store_true", help="show recent races and averages")
    p.add_argument("--version", action="version", version=f"typerace {__version__}")
    args = p.parse_args(argv)
    if args.history:
        return show_history()
    picker = Picker(all_quotes(), args.length)
    os.environ.setdefault("ESCDELAY", "25")
    try:
        curses.wrapper(main, picker)
    except KeyboardInterrupt:
        pass
    return 0

