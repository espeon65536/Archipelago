import os
from enum import IntEnum
from functools import lru_cache
from typing import List, Optional

from BaseClasses import Region, Location

# TODO: find a suitable ID offset
id_offset = 0


class MLSSLocationType(IntEnum):
    NORMAL = 0
    TEXTBOX = 1
    SHOP = 2


class MLSSLocation(Location):
    def __init__(self, player: int, name: str = '', 
        mlss_address: Optional[int] = None,
        parent: Optional[Region] = None,
        vanilla_item: Optional[int] = None,
        location_type: MLSSLocationType = None,
        logic_data: List[int] = None,
    ):
        super().__init__(player, name, id_offset + mlss_address)
        self.mlss_address = mlss_address
        self.vanilla_item = vanilla_item
        self.location_type = location_type
        self.logic_string = logic_string
        # TODO: set logic based on logic string


# TODO: retrieve better name from data files
def get_location_name(addr: str):
    return f'MLSS {addr}'


def add_location(region: Region, data: str) -> MLSSLocation:
    # Format of location data:
    # address, vanilla item, location type, *logic
    # hammers, rose, brooch, fire, thunder, fruit, membership, winkle, beanstar, dress, mini, under, dash, crash
    data = data.split(',')
    name          = get_location_name(data[0])
    address       = int(data[0], base=16)
    vanilla_item  = int(data[1], base=16)
    location_type = MLSSLocationType(int(data[2]))
    logic_data    = list(map(lambda x: int(x), data[3:17]))

    loc = MLSSLocation(region.player, name, address, region, vanilla_item, location_type, logic_data)
    region.locations.append(loc)


def get_location_data(submodule: str):
    """Helper generator which yields each line of the location files."""
    location_files = ['AllAddresses', 'BrosItems', 'KeyItems', 'Shops', 'Espresso', 'Pants', 'Badges']
    for fname in location_files:
        path = os.path.join(submodule, 'items', f'{fname}.txt')
        with open(path, 'r') as f:
            yield f.readline()


def build_locations(region: Region, submodule: str) -> None:
    for dt in get_location_data(submodule):
        add_location(region, dt)


@lru_cache(maxsize=1)
def make_location_name_to_id(submodule: str):
    location_name_to_id = {}
    for dt in get_location_data(submodule):
        data = dt.split(',')
        name = get_location_name(data[0])
        address = id_offset + int(data[0], base=16)
        location_name_to_id[name] = address
    return location_name_to_id
