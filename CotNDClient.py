import asyncio
import json
import logging
import os
import socket
import time
from asyncio import StreamReader, StreamWriter

from CommonClient import CommonContext, server_loop, gui_enabled, console_loop, \
    ClientCommandProcessor, logger, get_base_parser
import Utils
from worlds import network_data_package

from worlds.cotnd.Items import item_table, bad_items, always_available_items

UDP_IP = "127.0.0.1"
UDP_PORT = 8980
UDP_TARGET = (UDP_IP, UDP_PORT)

cotnd_loc_name_to_id = network_data_package["games"]["Crypt of the Necrodancer Synchrony"]["location_name_to_id"]

def reverse_readline(filename, buf_size=8192):
    """A generator that returns the lines of a file in reverse order.
    Taken from https://stackoverflow.com/questions/2301789/how-to-read-a-file-in-reverse-order
    """
    with open(filename) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first 
                if buffer[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


class CotNDCommandProcessor(ClientCommandProcessor):
    def _cmd_deathlink(self):
        """Toggle deathlink."""
        if isinstance(self.ctx, CotNDContext):
            self.ctx.deathlink = not self.ctx.deathlink
            asyncio.create_task(self.ctx.update_death_link(self.ctx.deathlink), name="Update Deathlink")


class CotNDContext(CommonContext):
    command_processor = CotNDCommandProcessor
    items_handling = 0b111  # full remote

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.game = 'Crypt of the Necrodancer Synchrony'
        self.last_log_msg = ""
        self.game_watcher = asyncio.create_task(self.game_writer(), name="Game Watcher")
        self.game_reader = asyncio.create_task(self.game_reader(), name="Game Reader")
        self.nonce = str(int(time.time()))
        self.last_msg = {}
        self.deathlink = False
        self.deathlink_pending = False

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(CotNDContext, self).server_auth(password_requested)
        if not self.auth:
            logger.info('Enter slot name:')
            self.auth = await self.console_input()

        await self.send_connect()

    def run_gui(self):
        from kvui import GameManager

        class CotNDManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Crypt of the NecroDancer: Synchrony - Archipelago Client"

        self.ui = CotNDManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    def on_package(self, cmd, args):
        if cmd == 'Connected':
            slot_data = args['slot_data']
            self.reduce_starting_items = slot_data['reduce_starting_items']
            self.randomize_flawless = slot_data['randomize_flawless']
            self.free_samples = slot_data['free_samples']
            self.prevent_bad_samples = slot_data['prevent_bad_samples']
            self.char_counts = slot_data['char_counts']
            self.nonce = str(int(time.time()))

    def item_data(self, networkitem):
        return item_table[self.item_name_getter(networkitem.item)]

    def on_deathlink(self, data: dict):
        self.deathlink_pending = True
        super().on_deathlink(data)

    async def game_writer(self):
        while not self.slot:
            await asyncio.sleep(5)
        while not self.exit_event.is_set():
            try:
                await self.send_game_info()
            except Exception as e:
                logger.error(f'Error in writer: {e}')
            await asyncio.sleep(3)

    async def game_reader(self):
        while not self.slot:
            await asyncio.sleep(5)
        while not self.exit_event.is_set():
            try:
                await self.read_log_file()
            except Exception as e:
                logger.error(f'Error in reader: {e}')
            await asyncio.sleep(1)

    # Send information to the game over a UDP connection
    async def send_game_info(self):

        # Which items to spawn
        item_state = {}
        item_names_received = always_available_items | set(map(lambda item: self.item_name_getter(item.item), self.items_received))
        for name, info in item_table.items():
            if info[1] in {'Character', 'Junk', 'Trap'}:
                continue
            if type(info[2]) == list:
                for s in info[2]:
                    item_state[s] = name in item_names_received or (not self.reduce_starting_items and info[3])
            else:
                item_state[info[2]] = name in item_names_received or (not self.reduce_starting_items and info[3])

        # Chests to replace
        replace_chests = set()
        for name in map(self.location_name_getter, self.missing_locations):
            if 'Chest' in name:
                pieces = name.split()  # [char] [num] - Chest [level]
                if pieces[2] == '-':
                    del pieces[1]
                replace_chests.add(f'{pieces[0]} {pieces[3]}')

        # Characters/item list for players to receive
        pending_items = []
        characters = []
        for item in self.items_received:
            item_name = self.item_name_getter(item.item)
            data = item_table[item_name]
            if data[1] == 'Character':
                characters.append(item_name[7:])
            if data[1] in {'Junk', 'Trap'}:
                pending_items.append(data[2])
            if self.free_samples:
                if data[1] != 'Weapon':
                    if self.item_name_getter(item.item) in bad_items and self.prevent_bad_samples:
                        continue
                    pending_items.append(data[2] if isinstance(data[2], str) else data[2][0])
                else:
                    pending_items.append(data[2] if isinstance(data[2], str) else data[2][1]) # send titanium weapon

        # prevent async deathlink problems
        previous_deathlink_state = self.deathlink_pending
        data = {
            'nonce': self.nonce,
            'item_state': item_state,
            'characters': characters,
            'consumables': pending_items,
            'replace_chests': list(replace_chests),
            'flawless': self.randomize_flawless,
            'deathlink_enabled': self.deathlink,
            'deathlink_pending': previous_deathlink_state,
        }
        if previous_deathlink_state:
            self.deathlink_pending = False

        # Only send if necessary to prevent spamming IPC connection
        if data != self.last_msg:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(f"archipelago:{json.dumps(data)}".encode(), UDP_TARGET)
            self.last_msg = data

    # Retrieve information from the game's log files
    async def read_log_file(self):

        synchrony_dir = Utils.get_options()['cotnd_options']['synchrony']
        logfile = 'Synchrony.log'
        new_last = ''
        new_items = []
        try:
            reader = reverse_readline(os.path.join(synchrony_dir, logfile))
        except FileNotFoundError:
            logger.error('Synchrony logfile not found. Make sure the path in host.yaml points to your Synchrony folder.')
            return

        for line in reader:
            if new_last == '':
                new_last = line # set the new last_log_msg
            if line == self.last_log_msg: # we found a message we already read, so break
                break
            if '[Archipelago]' not in line:
                continue
            info = line.split('[info] ')[-1]
            token, msg_type, char, floor = info.split(' ')

            if token != self.nonce:
                # This message originated when the client sent a different nonce value to the game,
                # so we cannot safely consider it valid.
                self.last_msg = {}
                break

            search_pieces = []
            if msg_type == 'Item': # get the first matching location
                search_pieces = [char, floor]
            elif msg_type == 'Clear':
                if floor == '5-3' and char == 'Dove':
                    search_pieces = ['Dove', 'Clear']
                elif floor == '1-4' and char == 'Aria':
                    search_pieces = ['Aria', 'Clear']
                elif floor == '5-5' and char == 'Cadence':
                    search_pieces = ['Cadence', 'Clear']
                elif floor == '5-5' and char == 'Nocturna':
                    search_pieces = ['Nocturna', 'Clear']
                elif floor == '5-4' and char not in {'Aria', 'Cadence', 'Nocturna'}:
                    search_pieces = [char, 'Clear']
            elif msg_type == 'Death':
                if self.deathlink:
                    await self.send_death()

            if search_pieces:
                possible_locs = list(filter(lambda loc: all(p in self.location_name_getter(loc) for p in search_pieces),
                    self.missing_locations))
                if possible_locs:
                    new_items.append(sorted(possible_locs)[0])

        self.last_log_msg = new_last
        if new_items:
            await self.send_msgs([{
                "cmd": "LocationChecks",
                "locations": new_items,
            }])

        # The game is completed once all locations of type Clear are reached.
        clear_locs = list(filter(lambda loc: 'Clear' in self.location_name_getter(loc), self.missing_locations))
        if not clear_locs:
            await self.send_msgs([{
                "cmd": "StatusUpdate",
                "status": 30
            }])


if __name__ == '__main__':

    Utils.init_logging("CotNDClient")

    async def main():
        # multiprocessing.freeze_support()
        parser = get_base_parser()
        args = parser.parse_args()

        ctx = CotNDContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="Server Loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

    import colorama

    colorama.init()

    asyncio.run(main())
    colorama.deinit()
