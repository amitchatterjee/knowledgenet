import logging
from collections import deque

from pyrete.perms import permutations
from pyrete.graph import Node
from pyrete.utils import to_list
from pyrete.session import Session

class Ruleset:
    def __init__(self, name, rules):
        self.name = name
        # TODO add validations
        self.rules = rules

    def get_session(self):
        return Session(self.rules)

    def run(self, facts):
        return self.get_session().run(facts)

