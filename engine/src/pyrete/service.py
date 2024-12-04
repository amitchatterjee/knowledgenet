import uuid
from session import Session
from manual import Manual

def execute(manual, facts, global_ctx={}):
    resulting_facts = facts
    for ruleset in manual.rulesets:
        session = Session(ruleset, resulting_facts, f"{manual.id}:{ruleset.id}", global_ctx)
        resulting_facts = session.execute()
    return resulting_facts