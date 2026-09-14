"""Owner-slug subjects for FEC lookup.

Journalist ingest stays on journalist names and journalist_id.
These rows are the people and firm PACs already on the ownership
graph. A match attaches to the entity slug only — never to an outlet,
and never to journalists.fec_records.

Employer terms are the false-positive brake. Common names
(David Smith, Brian Roberts, Robert Pittman) must not ingest
without an employer hit.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OwnerFecSubject:
    slug: str
    full_name: str
    variations: tuple[str, ...]
    employer_terms: tuple[str, ...]
    require_employer: bool = True


OWNER_FEC_SUBJECTS: tuple[OwnerFecSubject, ...] = (
    OwnerFecSubject(
        "larry-ellison",
        "Lawrence Ellison",
        ("Larry Ellison", "Lawrence J Ellison"),
        ("oracle",),
        require_employer=False,  # Super PAC gifts often list a trust, not Oracle
    ),
    OwnerFecSubject(
        "david-ellison",
        "David Ellison",
        ("David D Ellison",),
        ("skydance", "paramount"),
    ),
    OwnerFecSubject(
        "larry-fink",
        "Laurence Fink",
        ("Larry Fink", "Laurence D Fink"),
        ("blackrock", "black rock"),
    ),
    OwnerFecSubject(
        "salim-ramji",
        "Salim Ramji",
        (),
        ("vanguard", "blackrock"),
    ),
    OwnerFecSubject(
        "ron-ohanley",
        "Ronald O'Hanley",
        ("Ron O'Hanley", "Ronald Ohanley", "Ronald P Ohanley"),
        ("state street",),
    ),
    OwnerFecSubject(
        "robert-iger",
        "Robert Iger",
        ("Robert A Iger", "Bob Iger"),
        ("disney", "walt disney"),
    ),
    OwnerFecSubject(
        "lachlan-murdoch",
        "Lachlan Murdoch",
        ("Lachlan K Murdoch",),
        ("fox", "news corp", "newscorp"),
        require_employer=False,  # Super PAC gifts may omit employer
    ),
    OwnerFecSubject(
        "brian-roberts",
        "Brian Roberts",
        ("Brian L Roberts",),
        ("comcast",),
    ),
    OwnerFecSubject(
        "ag-sulzberger",
        "A.G. Sulzberger",
        ("Arthur Gregg Sulzberger", "AG Sulzberger"),
        ("new york times", "ny times", "nyt"),
    ),
    OwnerFecSubject(
        "laurene-powell-jobs",
        "Laurene Powell Jobs",
        ("Laurene Powell-Jobs",),
        ("emerson",),
        require_employer=False,
    ),
    OwnerFecSubject(
        "david-d-smith",
        "David D Smith",
        ("David Smith",),
        ("sinclair",),
    ),
    OwnerFecSubject(
        "robert-pittman",
        "Robert Pittman",
        ("Bob Pittman", "Robert W Pittman"),
        ("iheart", "i heart", "clear channel"),
    ),
    OwnerFecSubject(
        "hilton-h-howell",
        "Hilton H Howell",
        ("Hilton Howell", "Hilton H Howell Jr"),
        ("gray television", "gray media", "atlantic american"),
    ),
    OwnerFecSubject(
        "patrick-soon-shiong",
        "Patrick Soon-Shiong",
        ("Patrick Soon Shiong",),
        ("nant", "los angeles times", "la times"),
        require_employer=False,
    ),
    OwnerFecSubject(
        "heath-freeman",
        "Heath Freeman",
        (),
        ("alden",),
    ),
    OwnerFecSubject(
        "philip-anschutz",
        "Philip Anschutz",
        ("Phil Anschutz",),
        ("anschutz",),
        require_employer=False,
    ),
    OwnerFecSubject(
        "jeff-bezos",
        "Jeff Bezos",
        ("Jeffrey Bezos", "Jeffrey P Bezos"),
        ("amazon",),
        require_employer=False,
    ),
    OwnerFecSubject(
        "michael-bloomberg",
        "Michael Bloomberg",
        ("Mike Bloomberg", "Michael R Bloomberg"),
        ("bloomberg",),
        require_employer=False,
    ),
)


def get_subject(slug: str) -> OwnerFecSubject | None:
    for row in OWNER_FEC_SUBJECTS:
        if row.slug == slug:
            return row
    return None


def owner_slugs() -> list[str]:
    return [row.slug for row in OWNER_FEC_SUBJECTS]
