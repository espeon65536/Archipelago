from ..AutoWorld import World, WebWorld

class MLSSWebWorld(WebWorld):
    # TODO: Add setup tutorials
    pass

class MLSSWorld(World):
    """TODO: Add game description here"""
    game: str = 'Mario & Luigi: Superstar Saga'
    web = MLSSWebWorld()

    @classmethod
    def assert_generate(cls) -> None:
        # TODO: Add check for MLSS ROM
        pass

    def create_regions(self) -> None:
        # Load locations from submodule files
        pass

    def create_items(self) -> None:
        # Load items from submodule files
        pass

    def pre_fill(self) -> None:
        # Place non-randomized items in their vanilla locations
        pass

    def generate_output(self) -> None:
        # Call into the submodule to generate the ROM
        pass
