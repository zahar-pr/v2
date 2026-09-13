from sources.base import SupplierSource
from sources.osm import OsmSource
from sources.twogis import TwoGisSource

SOURCES: tuple[SupplierSource, ...] = (OsmSource(), TwoGisSource())


def active() -> tuple[SupplierSource, ...]:
    return tuple(source for source in SOURCES if source.ready())
