"""
DYNAX Event System
"""

import json
import time
from typing import Dict, List
import dynax_db as db
import time


class ContractEvent:
    def __init__(self, contract_address, event_name, data):
        self.contract_address = contract_address
        self.event_name = event_name
        self.data = data
        self.timestamp = int(time.time())
        self.block_number = 0

    def to_dict(self):
        return {
            "contract_address": self.contract_address,
            "event_name": self.event_name,
            "data": self.data,
            "timestamp": self.timestamp,
            "block_number": self.block_number
        }

    @classmethod
    def from_dict(cls, data):
        event = cls(data["contract_address"], data["event_name"], data["data"])
        event.timestamp = data.get("timestamp", 0)
        event.block_number = data.get("block_number", 0)
        return event


class EventLog:
    def __init__(self):
        self.events = []
        self.events_by_contract = {}

    def emit(self, contract_address, event_name, data, block_number=0):
        event = ContractEvent(contract_address, event_name, data)
        event.block_number = block_number
        self.events.append(event)
        if contract_address not in self.events_by_contract:
            self.events_by_contract[contract_address] = []
        self.events_by_contract[contract_address].append(event)
        db.save_event(contract_address, event_name, data, block_number, int(time.time()))
        return event

    def get_events(self, contract_address=None, event_name=None, from_block=0, to_block=None):
        result = self.events
        if contract_address:
            result = [e for e in result if e.contract_address == contract_address]
        if event_name:
            result = [e for e in result if e.event_name == event_name]
        if from_block:
            result = [e for e in result if e.block_number >= from_block]
        if to_block:
            result = [e for e in result if e.block_number <= to_block]
        return [e.to_dict() for e in result]

    def get_contract_events(self, contract_address):
        events = self.events_by_contract.get(contract_address, [])
        return [e.to_dict() for e in events]

    def save_logs(self, filename="event_logs.json"):
        data = {
            "events": [e.to_dict() for e in self.events],
            "events_by_contract": {
                addr: [e.to_dict() for e in events]
                for addr, events in self.events_by_contract.items()
            }
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def load_logs(self, filename="event_logs.json"):
        try:
            events = db.load_all_events()
            self.events = []
            self.events_by_contract = {}
            for e in events:
                event = ContractEvent(e["contract_address"], e["event_name"], e["data"])
                event.block_number = e["block_number"]
                event.timestamp = e["timestamp"]
                self.events.append(event)
                if event.contract_address not in self.events_by_contract:
                    self.events_by_contract[event.contract_address] = []
                self.events_by_contract[event.contract_address].append(event)
            return True
        except Exception as e:
            print(f"Load error: {e}")
            return False

event_log = EventLog()
event_log.load_logs()
print("Event system loaded, events:", len(event_log.events))
