import os
from BaseClasses import Region, Location


class MLSSLocation(Location):
    pass


def parse_location_data(data: str) -> MLSSLocation:
    data = data.split(',')
    return None


def build_locations(region: Region, submodule: str) -> None:
    """Create all locations and bind onto main region."""
    location_files = ['AllAddresses', 'BrosItems', 'KeyItems', 'Shops', 'Espresso', 'Pants', 'Badges']
    for fname in location_files:
        path = os.path.join(submodule, 'items', f'{fname}.txt')
        with open(path, 'r') as f:
            loc = parse_location_data(f.readline())
            region.locations.append(loc)
