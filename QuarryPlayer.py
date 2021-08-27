from quarry.types.buffer import Buffer1_14
from quarry.types.chat import Message
from threading import Thread
from enum import Enum
from time import sleep

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
            sleep((self.world.ticks_per_second ** -1) * (self.fade_in + self.stay + self.fade_out))
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

        self.id = None
        self.type = None
        self.title = None

        self.held_item = None

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


class Inventory:

    def __init__(self, player):
        self.player: Player = player

        self.state_id = None
        self.window = Window(self)

        self.slots = SlotsArray(size=46)
        self.selected_slot = 0

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


class World:
    def __init__(self, quarry_client: _MinecraftQuarryClient):
        self.ticks_per_second = 20
        self.quarry_client = quarry_client
        self.title_information = TitleInformation(self)
        self.entities_object = EntitiesObject(self)

    @property
    def seconds_per_tick(self):
        return self.ticks_per_second ** -1


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
        [self.quarry_client.stop_sneaking, self.quarry_client.start_sneaking][value]()

    #def on_join_game_packet(self, packet):
    #    self.player_id = self.entity_id = packet.entity_id

    #def on_update_health_packet(self, packet):
    #    self.health, self.food, self.food_saturation = packet.health, packet.food, packet.food_saturation