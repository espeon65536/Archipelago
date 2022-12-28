import os

submodule: str = 'MLSSRandomizer'
# TODO: find suitable id offset
id_offset: int = 0

def get_submodule_file(*args):
    head, _ = os.path.split(__file__)
    return os.path.join(head, submodule, *args)
