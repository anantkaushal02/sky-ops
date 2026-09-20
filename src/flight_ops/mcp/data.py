"""In-memory mock aviation data used by the MCP tool server.

This is fake, self-contained sample data so the whole system runs without
any real airline or weather API. Swap this module out for real data sources
without changing the tool signatures in server.py.
"""

import random
import string

FLIGHTS = [
    {
        "flight_number": "SK101",
        "airline": "SkyOps Air",
        "origin": "JFK",
        "destination": "LAX",
        "departure_time": "2026-09-22T08:00:00",
        "arrival_time": "2026-09-22T11:15:00",
        "tail_number": "N101SK",
        "status": "on_time",
        "price_usd": 312.0,
    },
    {
        "flight_number": "SK202",
        "airline": "SkyOps Air",
        "origin": "JFK",
        "destination": "LAX",
        "departure_time": "2026-09-22T14:30:00",
        "arrival_time": "2026-09-22T17:50:00",
        "tail_number": "N202SK",
        "status": "delayed",
        "price_usd": 289.0,
    },
    {
        "flight_number": "SK303",
        "airline": "SkyOps Air",
        "origin": "ORD",
        "destination": "SEA",
        "departure_time": "2026-09-22T09:45:00",
        "arrival_time": "2026-09-22T12:10:00",
        "tail_number": "N303SK",
        "status": "on_time",
        "price_usd": 198.0,
    },
]

WEATHER_BY_AIRPORT = {
    "JFK": {
        "conditions": "clear",
        "visibility_miles": 10,
        "wind_mph": 12,
        "advisory": None,
    },
    "LAX": {
        "conditions": "light rain",
        "visibility_miles": 6,
        "wind_mph": 18,
        "advisory": "gusty crosswinds on approach",
    },
    "ORD": {
        "conditions": "thunderstorms",
        "visibility_miles": 3,
        "wind_mph": 30,
        "advisory": "ground stop possible",
    },
    "SEA": {
        "conditions": "overcast",
        "visibility_miles": 8,
        "wind_mph": 9,
        "advisory": None,
    },
}

MAINTENANCE_BY_TAIL_NUMBER = {
    "N101SK": {
        "airworthy": True,
        "open_squawks": [],
        "last_inspection": "2026-09-10",
    },
    "N202SK": {
        "airworthy": True,
        "open_squawks": ["cabin light flickering, row 14"],
        "last_inspection": "2026-09-05",
    },
    "N303SK": {
        "airworthy": False,
        "open_squawks": ["APU inoperative, ground power required"],
        "last_inspection": "2026-08-30",
    },
}

BOOKINGS: dict[str, dict] = {}


def find_flight(flight_number: str) -> dict | None:
    for flight in FLIGHTS:
        if flight["flight_number"] == flight_number:
            return flight
    return None


def generate_confirmation_number() -> str:
    suffix = "".join(random.choices(string.digits, k=5))
    return f"CONF-{suffix}"
