import uuid
from session import Session
from knowledge import Knowledge

def execute(knowledge, facts, global_ctx={}):
    resulting_facts = facts
    for ruleset in knowledge.rulesets:
        session = Session(ruleset, resulting_facts, uuid.uuid1(), global_ctx)
        resulting_facts = session.execute()
    return resulting_facts