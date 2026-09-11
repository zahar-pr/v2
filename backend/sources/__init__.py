from sources.base import SupplierSource
from sources.osm import OsmSource

SOURCES: tuple[SupplierSource, ...] = (OsmSource(),)
