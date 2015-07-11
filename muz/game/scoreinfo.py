
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from collections import namedtuple

ScoreInfo = namedtuple("ScoreInfo", ["name", "threshold", "breakscombo", "score"])

values = (
    ScoreInfo("Miss",   1000, True,     0),
    ScoreInfo("Bad",     400, True,    10),
    ScoreInfo("Good",    200, True,    25),
    ScoreInfo("Great",   100, False,   50),
    ScoreInfo("Perfect",  50, False,  100)
)

miss, bad, good, great, perfect = values

