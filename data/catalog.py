"""Activity catalog

In production this data comes from AWS RDS PostgreSQL.
The dict below serve as the prototype / local-dev fallback.
"""

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

