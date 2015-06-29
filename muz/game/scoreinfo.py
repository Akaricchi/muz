
from __future__ import absolute_import

from collections import namedtuple

ScoreInfo = namedtuple("Timing", ["name", "threshold", "breakscombo", "score"])

values = (
    ScoreInfo("Miss",   1000, True,     0),
    ScoreInfo("Bad",     400, True,    10),
    ScoreInfo("Good",    200, True,    25),
    ScoreInfo("Great",   100, False,   50),
    ScoreInfo("Perfect",  50, False,  100)
)

miss, bad, good, great, perfect = values

