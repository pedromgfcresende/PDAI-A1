"""Activity catalog, demo clients, add-ons, and pickup locations.

In production this data comes from AWS RDS PostgreSQL via SQLAlchemy.
The dicts below serve as the prototype / local-dev fallback.
"""

DEMO_CLIENTS: dict = {
    "Acme Corp \u2013 Porto": {
        "client_name": "Acme Corp",
        "email": "contact@acme.pt",
        "group_size": 15,
        "date": "2026-03-15",
        "locations": ["Porto"],
        "duration_hours": 6,
        "preferences": ["adventure", "cultural"],
        "budget_per_person": 150,
        "special_requests": "First time in Portugal, avoid heights",
        "session_id": "evt-2026001",
    },
    "TechCorp \u2013 Sintra": {
        "client_name": "TechCorp",
        "email": "events@techcorp.com",
        "group_size": 25,
        "date": "2026-05-20",
        "locations": ["Sintra"],
        "duration_hours": 8,
        "preferences": ["adventure", "cultural", "food"],
        "budget_per_person": 200,
        "special_requests": "Several vegetarians",
        "session_id": "evt-2026002",
    },
}

ACTIVITY_CATALOG: list[dict] = [
    {
        "name": "Jeeps",
        "display": "Jeeps \u2014 \u20ac400/jeep per 4h block, 6 ppl/jeep",
        "type": "transport",
        "unit_price": 400.0,
        "capacity_per_unit": 6,
        "time_block_hours": 4,
    },
    {
        "name": "Walking",
        "display": "Walking \u2014 \u20ac10/person per hour",
        "type": "transport",
        "unit_price": 10.0,
        "per_person": True,
        "time_block_hours": 1,
    },
    {
        "name": "RZR",
        "display": "RZR \u2014 \u20ac200/car per 2h block, 2 ppl/car",
        "type": "transport",
        "unit_price": 200.0,
        "capacity_per_unit": 2,
        "time_block_hours": 2,
    },
]

# Flat fee unless noted; per-person items listed separately
ADD_ONS: dict = {
    "Professional Photography": 200,
    "Drone Footage": 350,
    "Team Building Facilitator": 400,
    "Welcome Gift Pack": 15,    # per person
    "Custom Team Jerseys": 25,  # per person
}

# price_from = pickup cost, price_to = drop-off cost
PICKUP_LOCATIONS: dict = {
    "Extremo HQ (Cascais)": {"lat": 38.737, "lng": -9.394, "price_from": 0, "price_to": 0},
    "Lisbon Centro": {"lat": 38.722, "lng": -9.139, "price_from": 80, "price_to": 80},
    "Cascais Hotels": {"lat": 38.697, "lng": -9.421, "price_from": 30, "price_to": 30},
}

# Add-ons whose price is multiplied by group size
PER_PERSON_ADDONS: frozenset = frozenset({"Welcome Gift Pack", "Custom Team Jerseys"})
