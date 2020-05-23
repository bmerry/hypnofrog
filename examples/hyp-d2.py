#!/usr/bin/env python3
import sys

from hypothesis.strategies import composite, integers, sampled_from, lists, tuples, just, deferred
import hypnofrog


bracket = deferred(lambda: (just('') | brackets).map(lambda x: '(' + x + ')'))
brackets = lists(bracket, min_size=1).map(''.join)


@composite
def make_case(draw):
    costs = integers(1, 9000)
    p = draw(brackets)
    K = len(p)
    L = draw(lists(costs, min_size=K, max_size=K))
    R = draw(lists(costs, min_size=K, max_size=K))
    P = draw(lists(costs, min_size=K, max_size=K))
    pos = integers(1, K)
    S = draw(lists(pos, min_size=1, max_size=100))
    Q = len(S)
    E = draw(lists(pos, min_size=Q, max_size=Q))
    return hypnofrog.make_input(1, (len(p), len(E)), p, L, R, P, S, E)


sys.exit(hypnofrog.run(make_case()))
