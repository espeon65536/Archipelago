from BaseClasses import Item
from .Utils import id_offset


class MLSSItem(Item):
    pass


def make_item_name_to_id():
    item_name_to_id = {}
    with open('ItemNames.txt', 'r') as f:
        line = f.readline()
        dt = line.split('-')
        code = int(dt[0].strip(), base=16)
        name = dt[1].strip()
        item_name_to_id[name] = id_offset + code
    return item_name_to_id
