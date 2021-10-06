from quarry.types.buffer import Buffer1_14
from quarry.types.chat import Message
from threading import Thread
from enum import Enum
from typing import Dict
from bitstring import BitStream
import numpy as np
import time

_MinecraftQuarryClient = object
if __name__ == '__main__':
    from MinecraftQuarryClient import MinecraftQuarryClient
    _MinecraftQuarryClient = MinecraftQuarryClient


def thread(func):
    def wrapper(*args, **kwargs):
        t = Thread(target=func, args=(*args,), kwargs=kwargs)
        t.start()
        return t

    return wrapper


class TitleInformation:
    def __init__(self, world):
        self.world: World = world

        # Time is given in ticks (int)
        self.fade_in = 0
        self.stay = 0
        self.fade_out = 0

        self.actual_title = Message("")
        self._title_queue = []
        self._title_being_processed = False
        self.actual_subtitle = Message("")
        self._subtitle_queue = []
        self._subtitle_being_processed = False

    @thread
    def _start_processing(self, array_name, property_name, callback, process_variable=""):

        if process_variable:
            setattr(self, process_variable, True)

        for i in getattr(self, array_name):
            if i.to_bytes() == getattr(self, property_name).to_bytes():
                continue
            setattr(self, property_name, i)
            callback(i)
            time.sleep((self.world.ticks_per_second ** -1) * (self.fade_in + self.stay + self.fade_out))
            getattr(self, array_name).pop()

        if process_variable:
            setattr(self, process_variable, False)

    @property
    def title(self):
        return self.actual_title

    @title.setter
    def title(self, value):
        self._title_queue.append(value)
        if not self._title_being_processed:
            self._start_processing('_title_queue', 'actual_title', self.world.quarry_client.on_update_title_text,
                                   process_variable='_title_being_processed')

    @property
    def subtitle(self):
        return self.actual_subtitle

    @subtitle.setter
    def subtitle(self, value):
        self._subtitle_queue.append(value)
        if not self._subtitle_being_processed:
            self._start_processing('_subtitle_queue', 'actual_subtitle',
                                   self.world.quarry_client.on_update_subtitle_text,
                                   process_variable='_subtitle_being_processed')


class SlotsArray:
    def __init__(self, size: int = 0):
        self._array = [b'\x00'] * int(size)

    def __getitem__(self, key):
        slot_s = self._array[key]
        if type(slot_s) is not list:
            return Buffer1_14(slot_s).unpack_slot()

        return [Buffer1_14(x).unpack_slot() for x in slot_s]

    def __setitem__(self, key, value):
        if type(value) is dict:
            value = Buffer1_14().pack_slot(**value)

        try:
            self._array[key] = value
        except:
            print("ERROR AT", key)

    def __len__(self):
        return len(self._array)


class Slot:
    def __init__(self):
        self.present = False
        self.item_id = None
        self.item_count = None
        self.optional_nbt = None

    def from_bytes(self, buffer):
        buff = Buffer1_14(buffer)
        self.item_id = buff.unpack_varint()
        self.present = buff.unpack('?')
        if self.present:
            (
                self.item_count,
                self.optional_nbt
            ) = (buff.unpack('B'), buff.unpack_nbt())

        return self

    def to_bytes(self):
        buff = Buffer1_14()
        buff.add(buff.pack('B', self.present))

        if self.present:
            buff.add(
                buff.pack_varint(self.item_id) +
                buff.pack('B', self.item_count) +
                buff.pack_nbt(self.optional_nbt)
            )

        return buff.read()


class Window:
    types = [
        {
            "name": "generic_9x1",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "main_inventory": [
                    9,
                    44
                ]
            },
            "full_size": 45
        },
        {
            "name": "generic_9x2",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "row_1": [
                    9,
                    17
                ],
                "main_inventory": [
                    18,
                    53
                ]
            },
            "full_size": 54
        },
        {
            "name": "generic_9x3",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "row_1": [
                    9,
                    17
                ],
                "row_2": [
                    18,
                    26
                ],
                "main_inventory": [
                    27,
                    62
                ]
            },
            "full_size": 63
        },
        {
            "name": "generic_9x4",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "row_1": [
                    9,
                    17
                ],
                "row_2": [
                    18,
                    26
                ],
                "row_3": [
                    27,
                    35
                ],
                "main_inventory": [
                    36,
                    71
                ]
            },
            "full_size": 72
        },
        {
            "name": "generic_9x5",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "row_1": [
                    9,
                    17
                ],
                "row_2": [
                    18,
                    26
                ],
                "row_3": [
                    27,
                    35
                ],
                "row_4": [
                    36,
                    44
                ],
                "main_inventory": [
                    45,
                    80
                ]
            },
            "full_size": 81
        },
        {
            "name": "generic_9x6",
            "ranges": {
                "row_0": [
                    0,
                    8
                ],
                "row_1": [
                    9,
                    17
                ],
                "row_2": [
                    18,
                    26
                ],
                "row_3": [
                    27,
                    35
                ],
                "row_4": [
                    36,
                    44
                ],
                "row_5": [
                    45,
                    53
                ],
                "main_inventory": [
                    54,
                    89
                ]
            },
            "full_size": 90
        },
        {
            "name": "generic_3x3",
            "ranges": {
                "row_0": [
                    0,
                    2
                ],
                "row_1": [
                    3,
                    5
                ],
                "row_2": [
                    6,
                    8
                ],
                "main_inventory": [
                    9,
                    44
                ]
            },
            "full_size": 45
        },
        {
            "name": "anvil",
            "ranges": {
                "first_item": (0, 0),
                "second_item": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "beacon",
            "ranges": {
                "payment_item": (0, 0),
                "main_inventory": (1, 36)
            },
            "full_size": 37
        },
        {
            "name": "blast_furnace",
            "ranges": {
                "ingredient": (0, 0),
                "fuel": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "brewing_stand",
            "ranges": {
                "bottles": (0, 2),
                "ingredient": (3, 3),
                "blaze_power": (4, 4),
                "main_inventory": (5, 40)
            },
            "full_size": 41
        },
        {
            "name": "crafting_table",
            "ranges": {
                "output": (0, 0),
                "input": (1, 9),
                "main_inventory": (10, 45)
            },
            "full_size": 46
        },
        {
            "name": "enchantment_table",
            "ranges": {
                "item": (0, 0),
                "lapis_lazuli": (1, 1),
                "main_inventory": (2, 37)
            },
            "full_size": 38
        },
        {
            "name": "furnace",
            "ranges": {
                "ingredient": (0, 0),
                "fuel": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "grindstone",
            "ranges": {
                "top": (0, 0),
                "bottom": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "hopper",
            "ranges": {
                "slots": (0, 4),
                "main_inventory": (5, 40)
            },
            "full_size": 41
        },
        {
            "name": "lectern",
            "ranges": {
                "book": (0, 0),
                "main_inventory": (1, 36),
            },
            "full_size": 37
        },
        {
            "name": "loom",
            "ranges": {
                "banner": (0, 0),
                "dye": (1, 1),
                "pattern": (2, 2),
                "output": (3, 3),
                "main_inventory": (4, 39)
            },
            "full_size": 40
        },
        {
            "name": "villager_trading",
            "ranges": {
                "first_item": (0, 0),
                "second_item": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "shulker_box",
            "ranges": {
                "row_0": (0, 8),
                "row_1": (9, 17),
                "row_2": (18, 26),
                "main_inventory": (27, 62)
            },
            "full_size": 63
        },
        {
            "name": "smoker",
            "ranges": {
                "ingredient": (0, 0),
                "fuel": (1, 1),
                "output": (2, 2),
                "main_inventory": (2, 38)
            },
            "full_size": 39
        },
        {
            "name": "cartography_table",
            "ranges": {
                "map": (0, 0),
                "paper": (1, 1),
                "output": (2, 2),
                "main_inventory": (3, 38)
            },
            "full_size": 39
        },
        {
            "name": "stonecutter",
            "ranges": {
                "input": (0, 0),
                "output": (1, 1),
                "main_inventory": (2, 37)
            },
            "full_size": 38
        }
    ]

    def __init__(self, inventory):
        self.inventory: Inventory = inventory

        self.name = ""
        self.ranges = {}
        self.full_size = None

        self.id = 0
        self.type = None
        self.title = None

        self.held_item = {'item': None}

        self.confirmations = []

    def _fix_confirmations_length(self, window_id, action_number):
        while window_id not in range(len(self.confirmations)):
            self.confirmations.append([])

        while action_number not in range(len(self.confirmations[window_id])):
            self.confirmations[window_id].append(None)

    def fix_confirmations_length(self, func):
        def wrapper(*args, **kwargs):
            window_id = kwargs.get('window_id', (list(args) + [None, None])[0])
            action_number = kwargs.get('action_number', (list(args) + [None, None])[1])
            self._fix_confirmations_length(window_id, action_number)

            func(*args, **kwargs)

        return wrapper

    #@fix_confirmations_length
    def wait_action_id(self, window_id, action_number):
        assert self.inventory.player.quarry_client.factory.quarry_protocol,\
            "Function does not exist in this minecraft version"

        self._fix_confirmations_length(window_id, action_number)

        while self.confirmations[window_id][action_number] is None:
            pass

        _accepted = self.confirmations[window_id][action_number]
        self.confirmations[window_id][action_number] = None

        return _accepted

    #@fix_confirmations_length
    def on_window_confirmation(self, window_id, action_number, accepted):
        self._fix_confirmations_length(window_id, action_number)

        self.confirmations[window_id][action_number] = accepted

    def get_range(self, _range):
        return self.ranges.get(_range, (0, len(self.inventory.slots)))

    def __getitem__(self, item):
        _range = self.ranges.get(item, (0, len(self.inventory.slots)))

        return self.inventory.slots[_range[0]:_range[1]]

    def create(self):
        _dict_info = Window.types[self.type]
        self.name = _dict_info['name']
        self.ranges = _dict_info['ranges']
        self.full_size = _dict_info['full_size']
        self.inventory.slots = SlotsArray(self.full_size)

    @property
    def state_id(self):
        return self.inventory.state_id

    @state_id.setter
    def state_id(self, value: int):
        self.inventory.state_id = value


class Inventory:

    def __init__(self, player):
        self.player: Player = player

        self.state_id = 0
        self.window = Window(self)

        self.slots = SlotsArray(size=46)
        self.selected_slot = 0

    def clear(self):
        del self.slots
        self.slots = SlotsArray(size=46)

    @staticmethod
    def get_slots_from_type():
        pass

    @property
    def selected_item(self):
        return self.slots[self.selected_slot]

    def on_window_items(self, window_id, count, slot_data, state_id=None, carried_item=None):
        if window_id == 0:
            for index in range(count):
                _item = slot_data[index]
                self.slots[index] = _item

        self.state_id = state_id

    def create_window(self, window_id, window_type, window_title):

        self.window.id, self.window.type, self.window.title = window_id, window_type, window_title
        self.window.create()

        return self


class EntitiesObject:
    def __init__(self, world):
        self.world: World = world

        self.entities: Dict[int, Entity] = {}


class Chunk:
    def __init__(self,
                 chunks,
                 chunk_x,
                 chunk_z,
                 primary_bit_mask,
                 height_maps,
                 biomes,
                 data,
                 block_entities):

        self.built = False
        self.chunks = chunks

        self.chunk_x = chunk_x
        self.chunk_z = chunk_z

        self.biomes = biomes
        self.height_map = height_maps
        self.primary_bit_mask = primary_bit_mask

        self._blocks = None
        self.data = data
        self.block_entities = block_entities

    @property
    def blocks(self):
        if self._blocks is None:
            return self._compute_data_to_blocks()

        return self._blocks

    def _compute_data_to_blocks(self):

        block_state_ids = []
        for non_air_blocks, bits_per_block, palette, data_array in self.data:
            offset = 64 % bits_per_block
            stream = BitStream(data_array)
            bits_per_long = 64 // bits_per_block

            # Variable needed because depending on the bits_per_block
            # the last long could contain more information than needed (ex. needs more 5 blocks to reach 4096 but has
            #                                                           more bits than 5 * bits_per_block)
            added_blocks = 0
            for i in range(stream.length // 64):  # Looping through each long in the data_array
                long_bit_stream = BitStream(stream.read(64))  # reads a whole long
                long_bit_stream.reverse()

                for _ in range(bits_per_long):
                    index = long_bit_stream.read(bits_per_block)
                    index.reverse()
                    if added_blocks < 4096:
                        block_state_ids.append(palette[index.uint])
                        added_blocks += 1

                long_bit_stream.read(offset)  # offset to fit block information into 64 bits (8bytes aka Long)

        block_state_ids.extend(0 for _ in range((16 ** 4) - len(block_state_ids)))
        self._blocks = np.concatenate(
            [
                # This splits the blocks array into 16x16x16 blocks (4096 blocks)
                # and then concatenates in the y axis for easy access
                # (chunk.blocks[ANY_Y_VALUE][Z from 0 to 16][X from 0 to 16])
                np.array(block_state_ids[i * 4096: (i + 1) * 4096], dtype='uint16').reshape((16, 16, 16)) for i in range(len(block_state_ids) // 4096)
            ]
        )
        self.built = True

        return self._blocks


class Chunks:

    def __init__(self, world):
        self.world = world
        self._chunks: Dict[tuple, Chunk] = {}
        self._computing_queue_status = False
        self._computing_queue = []

        self.processing_new_chunks: bool = False
        self.chunks_to_process = []

    def clear(self):
        self._chunks: Dict[tuple, Chunk] = {}
        self._computing_queue_status = False
        self._computing_queue = []
        self.processing_new_chunks: bool = False
        self.chunks_to_process = []

    def __getitem__(self, chunk_x_z) -> Chunk:
        _chunk = self._chunks.get(chunk_x_z, None)
        if type(_chunk) is bytes:
            self.load_new_chunk(*self.unpack_chunk_data(Buffer1_14(_chunk)))
        return self._chunks.get(chunk_x_z, None)

    def get_block(self, x, y, z):
        chunk_x, chunk_z = x // 16, z // 16
        if self[chunk_x, chunk_z] and self[chunk_x, chunk_z].built:
            return self[chunk_x, chunk_z].blocks[y][z % 16][x % 16]
        return None

    def new_block_change(self, x, y, z, block_id):
        chunk_x, chunk_z = x // 16, z // 16
        if self[chunk_x, chunk_z] and self[chunk_x, chunk_z].built:
            self[chunk_x, chunk_z].blocks[y][z % 16][x % 16] = block_id

    def new_multi_block_change(self, chunk_x, chunk_y, chunk_z, blocks):
        if self[chunk_x, chunk_z] and self[chunk_x, chunk_z].built:
            y_factor = chunk_y * 16
            for block_state_id, (x, y, z) in blocks:
                self[chunk_x, chunk_z].blocks[y + y_factor][z][x] = block_state_id

    @thread
    def _compute_blocks(self):

        if self._computing_queue_status:
            return -1

        self._generating_queue = True

        for chunk_x, chunk_z in self._computing_queue:

            data = self._chunks[(chunk_x, chunk_z)].data
            _blocks = self._chunks[(chunk_x, chunk_z)]._blocks

            for non_air_blocks, bits_per_block, palette, data_array in data:

                block_state_ids = \
                    [[palette[stream.read(bits_per_block).int] for _ in range(stream.length // bits_per_block)] for stream
                     in
                     [BitStream(data_array)]][0]

                _blocks.extend(block_state_ids)

        self._computing_queue_status = False

    def load_new_chunk(self,
                       chunk_x,
                       chunk_z,
                       primary_bit_mask,
                       height_maps,
                       biomes,
                       data,
                       block_entities):

        self._chunks[(chunk_x, chunk_z)] = Chunk(
            self,
            chunk_x,
            chunk_z,
            primary_bit_mask,
            height_maps,
            biomes,
            data,
            block_entities
        )

    def unpack_chunk_data(self, buff: Buffer1_14):
        chunk_x, chunk_z = buff.unpack('ii')

        bit_mask_length = buff.unpack_varint()
        primary_bit_mask = buff.unpack_array('q', bit_mask_length)
        bit_mask = BitStream()
        if primary_bit_mask:
            bit_mask = BitStream(', '.join(['0b' + bin(v)[2:].rjust(32, '0') for v in primary_bit_mask]))
            bit_mask.reverse()

        height_maps = buff.unpack_nbt()
        biomes_length = buff.unpack_varint()
        biomes = []
        for _ in range(biomes_length):
            biomes.append(buff.unpack_varint())

        size = buff.unpack_varint()
        _size_counter = buff.pos

        data = []
        while (buff.pos - _size_counter) < size:
            try:
                if not bit_mask.read(1).uint:
                    data.append((0, 4, [0], b'\x00' * (4096 // 2)))
                    continue
            except Exception as ex:
                (lambda *args, **kwargs: None)()

            non_air_blocks = buff.unpack('h')
            bits_per_block = buff.unpack('B')

            bits_per_block = 4 if bits_per_block <= 4 else bits_per_block

            palette_length = buff.unpack_varint()

            palette = []
            for _ in range(palette_length):
                palette.append(buff.unpack_varint())

            data_array_length = buff.unpack_varint()  # \x80\x02

            # data_array = buff.unpack_array('q', data_array_length)
            data_array = buff.read(8 * data_array_length)

            data.append((non_air_blocks, bits_per_block, palette.copy(), data_array))
        #data.extend(buff.unpack_chunk(bit_mask.uint))

        number_of_block_entities = buff.unpack_varint()

        block_entities = []
        for _ in range(number_of_block_entities):
            block_entities.append(buff.unpack_nbt())

        return (chunk_x,
                chunk_z,
                primary_bit_mask,
                height_maps,
                biomes,
                data,
                block_entities)

    @thread
    def _process_new_chunks(self):

        if self.processing_new_chunks:
            return

        self.processing_new_chunks = True
        while self.chunks_to_process:
            for buff in list(self.chunks_to_process):
                self.load_new_chunk(*self.unpack_chunk_data(Buffer1_14(buff).unpack_chunk()))
        self.processing_new_chunks = False

    def new_chunk_data(self, buffer: bytes):
        chunk_x, chunk_z = Buffer1_14(buffer).unpack('ii')
        self._chunks[(chunk_x, chunk_z)] = buffer


class World:
    def __init__(self, quarry_client: _MinecraftQuarryClient):
        self.dimension = None
        self.name = None
        self.hashed_seed = None
        self.is_debug = None
        self.is_flat = None
        self.max_players = None

        self.load_chunks = True
        self.chunks = Chunks(self)
        self.ticks_per_second = 20
        self.quarry_client: _MinecraftQuarryClient = quarry_client
        self.title_information = TitleInformation(self)
        self.entities_object = EntitiesObject(self)

        self.age = None
        self.time_of_day = None
        self._date_state_info = (
            (0, "day"),
            (6000, "noon"),
            (12000, "sunset"),
            (13000, "night"),
            (18000, "midnight"),
            (23000, "sunrise")
        )

    @property
    def seconds_per_tick(self):
        return self.ticks_per_second ** -1

    @property
    def day_state(self):
        if not self.time_of_day:
            return None

        for index, (ticks, state) in enumerate(self._date_state_info):
            if self.time_of_day < ticks:
                return self._date_state_info[index - 1][1]

    def get_block_state_id(self, x, y, z):
        chunk = self.chunks[x // 16, z // 16]
        if chunk is None:
            return None

        return chunk.blocks[y][z % 16][x % 16]


class Entity:
    def __init__(self, quarry_client: _MinecraftQuarryClient):
        self.quarry_client = quarry_client

        self.entity_id = None
        self.UUID = None

        self.is_player = False

        self.x = None
        self.y = None
        self.z = None
        self.yaw = None
        self.pitch = None
        self.on_ground = True

        self.health = None
        self.food = None
        self.food_saturation = None

    def update_option(self, **kwargs):
        for name, value in kwargs.items():
            if value is not None:
                setattr(self, name, value)

    def update_from_delta(self, x=None, y=None, z=None):
        self.x += [x, 0][x is None] / 128 / 32
        self.y += [y, 0][y is None] / 128 / 32
        self.z += [z, 0][z is None] / 128 / 32


class BlockFace(Enum):
    BOTTOM = 0
    TOP = 1
    NORTH = 2
    SOUTH = 3
    WEST = 4
    EAST = 5


class Hand(Enum):
    MAIN = 0
    OFF = 1


class DiggingStatus(Enum):
    START_DIGGING = 0
    CANCEL_DIGGING = 1
    FINISH_DIGGING = 2
    DROP_ITEM_STACK = 3
    DROP_ITEM = 4
    SHOOT_ARROW = 5
    FINISH_EATING = 5
    SWAP_ITEM = 6


class Player(Entity):
    def __init__(self, quarry_client: _MinecraftQuarryClient):
        super(Player, self).__init__(quarry_client)
        self.quarry_client_settings = dict(
            locale="en_US",
            view_distance=0b00000001,
            chat_mode=0,
            chat_colors=True,
            displayed_skin_parts=0x7f,
            main_hand=1,
            disable_text_filtering=True
        )

        self.gamemode = None

        self.inventory = Inventory(self)

        self.username = None
        self.display_name = None

        self.player_id = None
        self.is_player = True

        self._sneaking = False

    @property
    def sneaking(self):
        return self._sneaking

    @sneaking.setter
    def sneaking(self, value):
        self._sneaking = value
        [self.quarry_client.stop_sneaking, self.quarry_client.start_sneaking][bool(value)]()
        time.sleep(self.quarry_client.world.seconds_per_tick)


class ConfirmationInformation:
    def __init__(self, name, response=None, stack=False, debug=False):
        self.name = name
        self.stack = stack
        self._response = response
        self.responses = []
        self.debug = False

    @property
    def status(self):
        if bool(self.responses):
            self._response = self.responses.pop(0)
            return True
        return False

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, value):
        if self.debug:
            print(value)
        self.responses.append(value)
        if not self.stack:
            while len(self.responses) > 1:
                self.responses.pop(0)


class Confirmations:
    def __init__(self, client: _MinecraftQuarryClient):
        self._confirmations = {}

        for method_name in filter(lambda m: m.startswith('_on_'), dir(client)):
            clear_name = method_name.lstrip('_on_')
            self._confirmations[clear_name] = ConfirmationInformation(clear_name)
            setattr(client, method_name, Confirmations.decorator(getattr(client, method_name), self._confirmations[clear_name]))

    @staticmethod
    def decorator(func, sensor):

        def wrapper(*args, **kwargs):
            sensor.response = (args, kwargs)
            return func(*args, **kwargs)

        return wrapper

    def __getattr__(self, item):
        if item in self._confirmations:
            return self._confirmations[item]

        raise AttributeError
