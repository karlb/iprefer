from time import perf_counter
from functools import total_ordering


@total_ordering
class measure_time:
    def __enter__(self):
        self.t = perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.e = perf_counter()

    def __float__(self):
        return float(self.e - self.t)

    def __coerce__(self, other):
        return (float(self), other)

    def __str__(self):
        return str(float(self))

    def __repr__(self):
        return str(float(self))

    def __lt__(self, other):
        return float(self) < other

    def __format__(self, spec):
        return float(self).__format__(spec)
