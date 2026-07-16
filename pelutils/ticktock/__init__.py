"""Time taking and profiling inspired by Matlab's ``tic``/``toc``.

Profiling normally means reaching for ``cProfile`` and squinting at a wall of
function-level statistics, or littering your code with ``time.perf_counter()``
calls and manual bookkeeping. ``TickTock`` sits in between: you wrap the code
sections *you* care about in named, nestable context managers and get back a
readable, tree-structured table of where the time went — with per-section totals,
hit counts, averages, and the percentage of the parent's time each section took.
The overhead per profile is tiny, so it is well suited to hot loops and can be
left in long-running code.

Quick start
-----------

.. code-block:: python

    from pelutils.ticktock import TT

    # Ad-hoc timing, Matlab style
    TT.tick()
    ...  # Some task
    seconds = TT.tock()

    # Profile named sections, nest them freely, then print a breakdown
    for n in range(100):
        with TT.profile("Outer task"):
            ...
            with TT.profile("Inner subtask"):
                ...
    print(TT)  # Pretty table of the full profile tree

``TT`` is a ready-to-use global instance and is all most code needs. When you need
isolation — most importantly one instance per thread, since profiling is not
thread-safe — construct your own with :class:`TickTock`. See :class:`TickTock` for
the full API, including ``hits`` for tight loops, ``do_at_interval`` for throttling
periodic tasks, and ``fuse``/``fuse_multiple`` for combining results across
processes.
"""

from ._ticktock import TT, Profile, TickTock, TickTockException

__all__ = ("TT", "Profile", "TickTock", "TickTockException")
