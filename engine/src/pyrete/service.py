import uuid
from session import Session
from repository import Repository

def execute(repository, facts, global_ctx={}):
    resulting_facts = facts
    for ruleset in repository.rulesets:
        session = Session(ruleset, resulting_facts, f"{repository.id}:{ruleset.id}", global_ctx)
        resulting_facts = session.execute()
    return resulting_facts