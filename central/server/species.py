"""What animal a tag is on, and how confidently we know it.

Two different claims get made about a tag's species and they are NOT the same
strength of evidence:

  registry - somebody entered this tag into the lab's registry and said what it
             is riding on. A fact about a specific transmitter.
  band     - the frequency falls in a range this lab allocates to a project
             ("the 164 MHz tags are otters"). A convention, not a measurement,
             and it is right about a tag only for as long as the allocation
             holds.

Collapsing those two into one label is the same mistake the detector made when
`_is_frequency_whitelisted()` returned True for frequencies nobody configured:
a guess rendered identically to a fact reads as a fact, and a station published
30 phantom tags because of it. So `resolve()` always reports WHICH of the two
produced the answer, and the dashboard draws a band-derived icon faintly.

Adding a species needs an icon asset in server/static/img/species/, so the
catalog is code rather than a table - you cannot usefully add a row without a
deploy anyway. Per-tag assignment is the part that needs no deploy, and that
lives in tag_registry.species.
"""
from typing import Optional

def catalog_entry(key: Optional[str]) -> Optional[dict]:
    """The catalog row for a key, or None if the key is unknown/absent.

    Unknown keys return None rather than raising: a species string can outlive
    the catalog entry that defined it (an old DB row, a rolled-back deploy),
    and a dashboard that 500s because a tag names a species it no longer
    recognises is worse than one that shows no icon.
    """
    ...

def species_from_band(frequency_khz) -> Optional[str]:
    """The species this lab allocates to the frequency, if any."""
    ...

def resolve(frequency_khz, registry_species: Optional[str]=None) -> dict:
    """Decide a tag's species and say where the answer came from.

    Args:
        frequency_khz: the tag's frequency.
        registry_species: the species recorded against this tag in
            tag_registry, when the tag is a registered one. Wins outright: it
            is about this transmitter, where a band rule is about the range.

    Returns a dict that is always the same shape, so a template can render it
    without branching:
        key        - catalog key, or None
        label      - display name, or None
        abbr       - short all-caps form, shown in the icon's box when a
                     species has no artwork yet (a full name is illegible at
                     icon size, and a variable-width one breaks the column)
        icon       - '/static/img/species/<file>', or None
        source     - 'registry' | 'band' | None
        certain    - True only for 'registry'. The dashboard draws an uncertain
                     icon faintly and says so on hover, so a convention never
                     reads on screen as a verified fact.
    """
    ...
MATCH_TOLERANCE_KHZ = 2

class Resolver:
    """Resolves species for rows that carry a frequency but no species column.

    A detection in the `tags` table, or a row on the season whitelist, is not a
    registry row and has nowhere to store a species. Both are nevertheless the
    same physical transmitter as a registry entry at the same frequency, so the
    species is looked up there rather than duplicated - one place to edit, and
    no way for two copies to disagree.
    """

    def __init__(self, registry_rows=None):
        ...

    def registry_species_for(self, frequency_khz) -> Optional[str]:
        """The species of the nearest registered tag within tolerance."""
        ...

    def resolve(self, frequency_khz, registry_species: Optional[str]=None) -> dict:
        """As module-level resolve(), but falling back to the registry index."""
        ...

    def annotate(self, rows, freq_field: str='frequency_khz', species_field: str='species') -> list:
        """Attach a resolved species dict to every row of a payload.

        Overwrites 'species' with the resolved dict, so read the raw string
        first if you need it.
        """
        ...

def annotate(rows, freq_field: str='frequency_khz', species_field: str='species') -> list:
    """Annotate rows that already carry their own species column."""
    ...

def options() -> list:
    """Catalog as a list for a <select>, stable order, icon path resolved."""
    ...

def is_valid(key: Optional[str]) -> bool:
    """Is this a species key the catalog knows? Empty/None clears the field."""
    ...
