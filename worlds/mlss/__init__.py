import os

from .Location import build_locations, make_location_name_to_id

from BaseClasses import Region, RegionType, Entrance
from ..AutoWorld import World, WebWorld


submodule: str = 'MLSSRandomizer'


class MLSSWebWorld(WebWorld):
    # TODO: Add setup tutorials
    pass


class MLSSWorld(World):
    """TODO: Add game description here"""
    game: str = 'Mario & Luigi: Superstar Saga'
    web = MLSSWebWorld()

    location_name_to_id = make_location_name_to_id(submodule)
    item_name_to_id = make_item_name_to_id()

    @classmethod
    def assert_generate(cls) -> None:
        # TODO: Add check for MLSS ROM
        pass

    def create_regions(self) -> None:
        # Setup standard AP regions
        menu_region = Region('Menu', RegionType.Generic, '', self.player, self.multiworld)
        main_region = Region('Beanbean Kingdom', RegionType.Generic, '', self.player, self.multiworld)
        entr = Entrance(self.player, 'New Game', menu_region)
        entr.connect(main_region)

        # Load locations from submodule files
        build_locations(main_region, submodule)

        # TODO: Set completion condition?

    def create_items(self) -> None:
        # Load items from submodule files
        pass

    def pre_fill(self) -> None:
        # Place non-randomized items in their vanilla locations
        pass

    def generate_output(self) -> None:
        # Call into the submodule to generate the ROM
        pass
