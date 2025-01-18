import logging
import sys

import pytest

from knowledgenet.container import Collector
from knowledgenet.helper import assign
from knowledgenet.rule import Rule,Fact
from knowledgenet.ruleset import Ruleset
from knowledgenet.repository import Repository
from knowledgenet.service import Service
from test_helpers.unit_facts import C1, K1

def test_nested_collectors():
    with pytest.raises(Exception) as e:
        Collector(of_type=Collector, group='all_child', 
            filter=lambda this,child: child.group == 'child')

def test_collector_group():
    with pytest.raises(Exception) as e:
        Collector(of_type=C1, filter=lambda this,child: child.group == 'child')

def test_whens():
    with pytest.raises(Exception) as e:
        Rule(id='r1', when=Collector)
            
def test_collector_sum_on_no_value():
    with pytest.raises(Exception) as e:
        rule_1 = Rule(id='r1',
                    when=Fact(of_type=Collector, group='sum_of_k1s', 
                            matches=lambda ctx,this: assign(ctx, sum=this.sum(), size=len(this.collection))))
        facts = [K1(1, name='k1'), K1(2, name='k2'), 
                Collector(of_type=K1, group='sum_of_k1s')]
        Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
   
def test_collector_variance_on_no_value():
    with pytest.raises(Exception) as e:    
        rule_1 = Rule(id='r1',
                    when=Fact(of_type=Collector, group='sum_of_k1s', 
                            matches=lambda ctx,this: assign(ctx, variance=this.variance(), size=len(this.collection))))
        facts = [K1(1, name='k1'), K1(2, name='k2'),
                Collector(of_type=K1, group='sum_of_k1s')]
        Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)

def test_collector_min_on_no_key():
    with pytest.raises(Exception) as e:    
        rule_1 = Rule(id='r1',
                    when=Fact(of_type=Collector, group='sum_of_k1s', 
                            matches=lambda ctx,this: assign(ctx, min=this.minimum(), size=len(this.collection))))
        facts = [K1(1, name='k1'), K1(2, name='k2'),
                Collector(of_type=K1, group='sum_of_k1s')]
        Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)

def test_collector_max_on_no_key():
    with pytest.raises(Exception) as e:    
        rule_1 = Rule(id='r1',
                    when=Fact(of_type=Collector, group='sum_of_k1s', 
                            matches=lambda ctx,this: assign(ctx, max=this.maximum(), size=len(this.collection))))
        facts = [K1(1, name='k1'), K1(2, name='k2'),
                Collector(of_type=K1, group='sum_of_k1s')]
        Service(Repository('repo1', [Ruleset('rs1', [rule_1])])).execute(facts)
