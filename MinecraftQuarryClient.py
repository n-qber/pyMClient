from twisted.internet import reactor
from quarry.net.client import ClientProtocol, ClientFactory
from quarry.net.auth import OfflineProfile, Profile
from quarry.types.buffer import Buffer1_14
from QuarryPlayer import Player, World, Entity, BlockFace, Hand, thread
from random import getrandbits
import time


class MinecraftQuarryClientFactory(ClientFactory):

    def buildProtocol(self, addr):
        self.quarry_protocol = self.protocol(self, addr)
        return self.quarry_protocol

    def __init__(self, *args, quarry_client, quarry_protocol=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.quarry_protocol: MinecraftQuarryClientProtocol = quarry_protocol
        self.quarry_client: MinecraftQuarryClient = quarry_client
        self.protocol.quarry_client = self.quarry_client


class MinecraftQuarryClientProtocol(ClientProtocol):
    def send_packet(self, name, *data):
        super().send_packet(name, *data)

    def __init__(self, *args, quarry_client=None, **kwargs):
        super(MinecraftQuarryClientProtocol, self).__init__(*args, **kwargs)
        if quarry_client:
            self.quarry_client: MinecraftQuarryClient = quarry_client

        self._transaction_ids = {}

    def packet_chunk_data(self, buff: Buffer1_14):
        chunk_x, chunk_z = buff.unpack('ii')
        bitmask_length = buff.unpack_varint()
        #buff.unpack_chunk()

    def packet_confirm_transaction(self, buff: Buffer1_14):
        #  before and including 1.16.5
        #  self.protocol_version < 755 -> True

        window_id, action_number, accepted = buff.unpack('bh?')

        self.quarry_client._on_window_confirmation(window_id, action_number, accepted)

    def packet_entity_teleport(self, buff: Buffer1_14):
        entity_id = buff.unpack_varint()
        x, y, z, yaw, pitch, on_ground = buff.unpack('dddbb?')

        self.quarry_client._on_entity_teleport(entity_id, x, y, z, yaw, pitch, on_ground)

    def packet_entity_look(self, buff: Buffer1_14):
        entity_id = buff.unpack_varint()
        yaw, pitch = buff.unpack('bb')
        on_ground = buff.unpack('?')

        self.quarry_client._on_entity_position_and_rotation(entity_id, on_ground=on_ground, yaw=yaw, pitch=pitch)

    def packet_entity_look_and_relative_move(self, buff: Buffer1_14):
        entity_id = buff.unpack_varint()
        delta_x, delta_y, delta_z = buff.unpack('hhh')
        yaw, pitch = buff.unpack('bb')
        on_ground = buff.unpack('?')

        self.quarry_client._on_entity_position_and_rotation(entity_id, delta_x, delta_y, delta_z, yaw, pitch, on_ground)

    def packet_entity_relative_move(self, buff: Buffer1_14):
        entity_id = buff.unpack_varint()
        delta_x, delta_y, delta_z = buff.unpack('hhh')
        on_ground = buff.unpack('?')

        self.quarry_client._on_entity_position_and_rotation(entity_id, delta_x, delta_y, delta_z, None, None, on_ground)

    def packet_spawn_player(self, buff: Buffer1_14):
        entity_id, player_uuid = buff.unpack_varint(), buff.unpack_uuid()
        x, y, z, yaw, pitch = buff.unpack('dddbb')

        self.quarry_client._on_visible_player(entity_id, player_uuid, x, y, z, yaw, pitch)

    def packet_open_window(self, buff: Buffer1_14):
        window_id = buff.unpack_varint()
        window_type = buff.unpack_varint()
        window_title = buff.unpack_chat()

        self.quarry_client._on_open_window(window_id, window_type, window_title)

    def packet_window_property(self, buff: Buffer1_14):
        window_id = buff.unpack('B')
        _property = buff.unpack('h')
        value = buff.unpack('h')

        self.quarry_client._on_window_property(window_id, _property, value)

    def packet_window_items(self, buff: Buffer1_14):
        window_id = buff.unpack('B')

        state_id = None
        if self.protocol_version >= 755:  # 1.17
            state_id = buff.unpack_varint()
            count = buff.unpack_varint()
        else:  # sub 1.17
            count = buff.unpack('h')

        slot_data = [buff.unpack_slot() for _ in range(count)]

        carried_item = None
        if self.protocol_version >= 755:  # 1.17
            carried_item = buff.unpack_slot()

        self.quarry_client._on_window_items(window_id, count, slot_data, state_id, carried_item)

    def packet_set_slot(self, buff: Buffer1_14):
        window_id = buff.unpack('b')

        state_id = None
        if self.protocol_version >= 755:  # 1.17
            state_id = buff.unpack_varint()

        slot, slot_data = (buff.unpack('h'), buff.unpack_slot())

        self.quarry_client._on_set_slot(window_id, slot, slot_data, state_id)

    def packet_set_title_text(self, buff: Buffer1_14):
        title_text = buff.unpack_chat()

        if title_text.value is not None:
            self.quarry_client._on_set_title_text(title_text)

    def packet_set_title_subtitle(self, buff: Buffer1_14):
        subtitle_text = buff.unpack_chat()

        if subtitle_text.value is not None:
            self.quarry_client._on_set_subtitle_text(subtitle_text)

    def packet_set_title_time(self, buff: Buffer1_14):

        fade_in, stay, fade_out = buff.unpack('iii')

        self.quarry_client._set_title_time(fade_in, stay, fade_out)

    def send_held_item_change(self, slot):
        buff = Buffer1_14()
        buff.add(buff.pack('h', slot))

        #self.send_client_settings()
        #self.send_plugin_message()
        self.send_packet('held_item_change', buff.read())

    def packet_held_item_change(self, buff: Buffer1_14):
        slot = buff.unpack('B')
        self.quarry_client.player.inventory.selected_slot = 36 + slot
        self.send_held_item_change(slot)

    def send_client_settings(self,
                             locale="en_US",
                             view_distance=0b00000010,
                             chat_mode=0,
                             chat_colors=True,
                             displayed_skin_parts=0x7f,
                             main_hand=1,
                             disable_text_filtering=True):

        buff = Buffer1_14()
        buff.add(
            buff.pack_string(locale) +
            buff.pack('b', view_distance) +
            buff.pack_varint(chat_mode) +
            buff.pack('?', chat_colors) +
            buff.pack('B', displayed_skin_parts) +
            buff.pack_varint(main_hand) +
            (buff.pack('B', disable_text_filtering)) * (self.protocol_version >= 755))

        self.send_packet('client_settings', buff.read())

    def packet_player_position_and_look(self, buff: Buffer1_14):

        x = buff.unpack('d')
        y = buff.unpack('d')
        z = buff.unpack('d')
        yaw = buff.unpack('f')
        pitch = buff.unpack('f')
        flags = buff.unpack('B')
        teleport_id = buff.unpack_varint()
        dismount_vehicle = False
        if self.protocol_version >= 755:
            dismount_vehicle = buff.unpack('B')

        if self.quarry_client._on_player_position_and_look(x, y, z, yaw, pitch, teleport_id, flags, dismount_vehicle) == -1:
            #  ABORT TELEPORT CONFIRM
            return

        #print("server sent", x, y, z, yaw, pitch)
        self.teleport_confirm(teleport_id)
        self.quarry_client.set_player_position_and_rotation(x, y, z, yaw, pitch)

    def set_player_position_and_rotation(self, x, y, z, yaw, pitch, on_ground=True):
        buff = Buffer1_14()
        buff.add(buff.pack('dddffB', x, y, z, yaw, pitch, on_ground))
        self.send_packet('player_position_and_look', buff.read())

    def set_player_position(self, x, y, z, on_ground=True):
        buff = Buffer1_14()
        #print(x, y, z)
        buff.add(buff.pack('dddB', x, y, z, on_ground))

        self.send_packet('player_position', buff.read())

    def teleport_confirm(self, teleport_id):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(teleport_id))

        self.send_packet('teleport_confirm', buff.read())

    def packet_unhandled(self, buff, name):
        if self.quarry_client.debug:
            print(f"[{name}] UNHANDLED: {buff.read()}")
            return
        buff.discard()

    def _generate_new_transaction_id(self):
        rn = getrandbits(32)
        rn -= rn & (2 ** 31)
        if rn in self._transaction_ids:
            return self._generate_new_transaction_id()
        return rn

    def send_plugin_message(self, channel='minecraft:brand', data='vanilla'):
        buff = Buffer1_14()
        buff.add(buff.pack_string(channel) + buff.pack_string(data))

        self.send_packet('plugin_message', buff.read())

    def packet_player_info(self, buff: Buffer1_14):
        buff.read()
        self.send_client_settings(**getattr(self.quarry_client.player, 'quarry_client_settings', dict()))
        self.send_plugin_message()

    #  DO NOT MESS WITH THIS METHOD
    def packet_login_success(self, buff):
        # 1.16.x
        if self.protocol_version >= 735:
            p_uuid = buff.unpack_uuid()
        # 1.15.x
        else:
            p_uuid = buff.unpack_string()
        p_display_name = buff.unpack_string()

        self.switch_protocol_mode("play")
        self.player_joined()

        while not self.protocol_mode == "play":
            continue

        self.quarry_client.player.UUID = p_uuid
        self.quarry_client.player.display_name = p_display_name

        if self.quarry_client.player.username in ["", None]:
            self.quarry_client.player.username = self.quarry_client.player.display_name

    def use_item(self, hand: int = 0):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(hand))

        self.send_packet('use_item', buff.read())

    def send_chat_message(self, message):
        buff = Buffer1_14()
        buff.add(buff.pack_string(message))

        self.send_packet('chat_message', buff.read())

    def swap_hands(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(6))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))
        self.send_packet('player_digging', buff.read())

    def packet_keep_alive(self, buff: Buffer1_14):
        self.send_packet('keep_alive', buff.read())

    def packet_combat_event(self, buff: Buffer1_14):
        event = buff.unpack_varint()

        if event == 2:  # DEAD
            player_id = buff.unpack_varint()  # killed entity
            entity_id = buff.unpack_varint()  # killing entity
            message = buff.unpack_string()
            if player_id == self.quarry_client.player.player_id:
                self.quarry_client.on_death(player_id, entity_id, message)
        buff.read()

    def packet_join_game(self, buff: Buffer1_14):
        self.quarry_client.player.player_id = self.quarry_client.player.entity_id = buff.unpack('i')
        buff.read()

    def player_joined(self, *args, **kwargs):
        super().player_joined()
        self.quarry_client._on_player_joined()

    def player_left(self):
        super().player_left()
        self.quarry_client.on_player_left()

    def respawn(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(0))

        self.send_packet('client_status', buff.read())

    def send_nbt_query(self, x, y, z):
        buff = Buffer1_14()

        transaction_id = self._generate_new_transaction_id()
        buff.add(buff.pack_varint(transaction_id))
        buff.add(buff.pack_position(x, y, z))

        self.send_packet('query_block_nbt', buff.read())

    def packet_update_health(self, buff):
        health = buff.unpack('f')
        food = buff.unpack_varint()
        food_saturation = buff.unpack('f')

        self.quarry_client._on_update_health(health, food, food_saturation)

    def update_held_item(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(5))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))

        self.send_packet('player_digging', buff.read())

    def drop_item(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(4))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))

        self.send_packet('player_digging', buff.read())

    def drop_stack(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(3))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))

        self.send_packet('player_digging', buff.read())

    def packet_chat_message(self, buff: Buffer1_14):
        message_object = buff.unpack_chat()
        position = buff.unpack('B')
        sender = buff.unpack_uuid()

        if sender == self.quarry_client.player.UUID:
            #  echo message from client (player)
            return

        string_message = None
        try:
            string_message = message_object.to_string()
        except:
            pass

        [self.quarry_client.on_chat_message,
         self.quarry_client.on_system_message,
         self.quarry_client.on_game_info_message][position](string_message, sender, message_object)

    def send_close_window(self, window_id):
        buff = Buffer1_14()
        buff.add(buff.pack('B', window_id))

        self.send_packet('close_window', buff.read())

    def send_click_window(self,
                          slot_number,
                          slot_data,
                          mode=0,
                          button=0,
                          state_id=None,
                          window_id=None,
                          new_slot_data_array=None,
                          action_id=None):

        if new_slot_data_array is None:
            new_slot_data_array = [(slot_number, {'item': None})]

        buff = Buffer1_14()
        buff.add(
            buff.pack('B', window_id or self.quarry_client.player.inventory.window.id or 0) +

            [b'', buff.pack_varint(state_id or getattr(self.quarry_client.player.inventory, 'state_id', 1) or 1)]\
                [self.protocol_version >= 755] +

            buff.pack('h', slot_number) +

            buff.pack('b', button) +

            [b'', buff.pack('h', action_id or getattr(self.quarry_client.player.inventory.window, 'action_id', 1) or 1)]\
                [self.protocol_version < 755] +

            buff.pack_varint(mode))

        if self.protocol_version >= 755:
            buff.add(
                buff.pack_varint(len(new_slot_data_array)) +
                b''.join([buff.pack('h', _slot) + buff.pack_slot(**_slot_data) for _slot, _slot_data in new_slot_data_array]))

        buff.add(buff.pack_slot(**slot_data))

        self.send_packet('click_window', buff.read())

    def send_start_breaking(self, x, y, z, face):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(0))
        buff.add(buff.pack_position(x, y, z))
        buff.add(buff.pack('B', face))

        self.send_packet('player_digging', buff.read())

    def send_stop_breaking(self, x, y, z, face, operation="break"):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(int(operation != "cancel") + 1))
        buff.add(buff.pack_position(x, y, z))
        buff.add(buff.pack('B', face))

        self.send_packet('player_digging', buff.read())

    def send_player_block_placement(self, hand, x, y, z, face, cursor_x, cursor_y, cursor_z, inside_block=False):
        buff = Buffer1_14()
        buff.add(
            buff.pack_varint(hand) +
            buff.pack_position(int(x), int(y), int(z)) +
            buff.pack_varint(face) +
            buff.pack('fff', cursor_x, cursor_y, cursor_z) +
            buff.pack('?', inside_block))

        self.send_packet('player_block_placement', buff.read())

    def send_window_confirm(self, *args, **kwargs):
        self.send_confirm_transaction(*args, **kwargs)

    def send_confirm_transaction(self, window_id, action_number, accepted):
        buff = Buffer1_14()
        buff.add(buff.pack('bh?', window_id, action_number, accepted))

        self.send_packet('confirm_transaction', buff.read())


class MinecraftQuarryClient:
    def __init__(self,
                 username: str,
                 email: str = "",
                 password: str = "",
                 humanized: bool = True,
                 debug: bool = False):

        self.factory = MinecraftQuarryClientFactory(username, quarry_client=self)
        self.factory.protocol = MinecraftQuarryClientProtocol

        self.player = Player(self)
        self.player.username = username

        self.world = World(self)

        self.debug = debug

        if password:
            self.factory.profile = None
            Profile.from_credentials(email, password).addCallback(self._set_factory_profile)
        else:
            self.factory.profile = OfflineProfile(username)

    def _set_factory_profile(self, profile):
        """
        Callback used for login operations which sets the
        `self.factory.profile` variable
        :param profile: Result of Profile.from_credentials(email, password)
        """
        self.factory.profile = profile

    def join_server(self, address: str, port: int = 25565):
        """
        Joins a minecraft world
        :param address: server address
        :param port: port to connect, minecraft default port is 25565
        """
        # Starting "reactor" which runs all networks operations
        # starts in a different thread to be able to continue
        # sending information in main thread
        from threading import Thread
        Thread(target=reactor.run, args=(False,)).start()

        # Waiting for login process
        while not self.factory.profile:
            continue

        # Actually connects and "joins the server"
        self.factory.connect(address, port)

        # Needed for bottom condition not to raise "'NoneType' has no 'protocol_mode'"
        while type(self.factory.quarry_protocol) is type(None):
            continue

        # Waits for minecraft protocol to switch to "play" mode
        # Waits for minecraft protocol to switch to "play" mode
        while self.factory.quarry_protocol.protocol_mode != 'play':
            continue

        # Waits for player to load a position on the server
        while all([getattr(self.player, attr) is None for attr in ['x', 'y', 'z', 'yaw', 'pitch']]):
            continue

    def _on_set_slot(self, window_id, slot, slot_data, state_id=None):

        if state_id:  # 1.17
            self.player.inventory.state_id = state_id

        if window_id == -1 and slot == -1:
            self.player.inventory.window.held_item = slot_data
            return

        self.player.inventory.window.id = window_id
        self.player.inventory.slots[slot] = slot_data

        self.on_set_slot(window_id, slot, slot_data, state_id)

    def on_set_slot(self, window_id, slot, slot_data, state_id=None):
        pass

    def _on_player_joined(self):
        return self.on_player_joined()

    def on_player_joined(self):
        print("Joined the game")

    def on_player_left(self):
        print("Left the game")

    def swap_hands(self):
        self.factory.quarry_protocol.swap_hands()

    def respawn(self):
        self.factory.quarry_protocol.respawn()

    def on_death(self, *args, **kwargs):
        self.respawn()

    def get_block_nbt(self):
        self.factory.quarry_protocol.send_nbt_query(0, 0, 0)

    def send_chat_message(self, message):
        self.factory.quarry_protocol.send_chat_message(message)

    def use_item(self, hand="main"):
        self.factory.quarry_protocol.use_item([0, 1][hand.lower() == "off"])
        self.factory.quarry_protocol.update_held_item()

    def on_update_health(self, health, food, food_saturation):
        pass

    def _on_update_health(self, health, food, food_saturation):
        self.player.health = health
        self.player.food = food
        self.player.food_saturation = food_saturation
        self.on_update_health(health, food, food_saturation)

    def drop_items(self, quantity: int = 1):
        if quantity >= 64:
            return self.factory.quarry_protocol.drop_stack()

        for _ in range(quantity):
            self.factory.quarry_protocol.drop_item()

    def _on_player_position_and_look(self, x, y, z, yaw, pitch, teleport_id, flags, dismount_vehicle=False):
        self.player.x = x
        self.player.y = y
        self.player.z = z
        self.player.yaw = yaw
        self.player.pitch = pitch
        return self.on_player_position_and_look(x, y, z, yaw, pitch, teleport_id, flags, dismount_vehicle)

    def on_player_position_and_look(self, x, y, z, yaw, pitch, teleport_id, flags, dismount_vehicle=False):
        pass

    def _on_game_info_message(self, text, sender, message_object):
        self.on_game_info_message(text, sender, message_object)

    def _on_system_message(self, text, sender, message_object):
        self.on_system_message(text, sender, message_object)

    def _on_chat_message(self, text, sender, message_object):
        self.on_chat_message(text, sender, message_object)

    def on_game_info_message(self, text, sender, message_object):
        pass

    def on_system_message(self, text, sender, message_object):
        pass

    def on_chat_message(self, text, sender, message_object):
        pass

    def _set_title_time(self, fade_in, stay, fade_out):
        self.world.title_information.fade_in = fade_in
        self.world.title_information.stay = stay
        self.world.title_information.fade_out = fade_out

    def _on_set_title_text(self, title_text):
        self.world.title_information.title = title_text
        #self.on_set_title_text(title_text)

    def on_update_title_text(self, title_text):
        pass

    def _on_set_subtitle_text(self, subtitle_text):
        self.world.title_information.subtitle = subtitle_text
        #self.on_set_subtitle_text(subtitle_text)

    def on_update_subtitle_text(self, subtitle_text):
        pass

    def set_player_position_and_rotation(self, x=None, y=None, z=None, yaw=None, pitch=None, on_ground=True):
        self.player.update_option(x=x, y=y, z=z, yaw=yaw, pitch=pitch, on_ground=on_ground)

        self.factory.quarry_protocol.set_player_position_and_rotation(
            self.player.x,
            self.player.y,
            self.player.z,
            self.player.yaw,
            self.player.pitch,
            on_ground)

    def move_player(self,
                    x: float = 0,
                    y: float = 0,
                    z: float = 0,
                    yaw: float = 0,
                    pitch: float = 0, on_ground=True):

        if not yaw and not pitch:
            return self.set_player_position(
                self.player.x + x,
                self.player.y + y,
                self.player.z + z,
                on_ground)

        self.set_player_position_and_rotation(
            self.player.x + x,
            self.player.y + y,
            self.player.z + z,
            self.player.yaw + yaw,
            self.player.pitch + pitch,
            on_ground)

    def _on_plugin_message(self, channel, data):
        self.on_plugin_message(channel, data)

    def on_plugin_message(self, channel, data):
        pass

    def _on_window_items(self, window_id, count, slot_data, state_id=None, carried_item=None):
        self.player.inventory.on_window_items(window_id, count, slot_data, state_id=state_id, carried_item=carried_item)
        self.on_window_items(window_id, count, slot_data, state_id, carried_item)

    def on_window_items(self, window_id, count, slot_data, state_id, carried_item):
        pass

    def _on_window_property(self, window_id, _property, value):
        self.on_window_property(window_id, _property, value)

    def on_window_property(self, window_id, _property, value):
        pass

    def _on_open_window(self, window_id, window_type, window_title):
        self.player.inventory.create_window(window_id, window_type, window_title)
        self.on_open_window(window_id, window_type, window_title)

    def on_open_window(self, window_id, window_type, window_title):
        pass

    def close_window(self, window_id=None):
        if window_id is None:
            window_id = self.player.inventory.window_id or 0

        self.factory.quarry_protocol.send_close_window(window_id)

    def click_slot(self, slot, _range=""):
        start = self.player.inventory.window.get_range(_range)[0]
        self.factory.quarry_protocol.send_click_window(start + slot, self.player.inventory.slots[start + slot])

    def set_player_position(self, x, y, z, on_ground):
        self.player.update_option(x=x, y=y, z=z, on_ground=on_ground)

        self.factory.quarry_protocol.set_player_position(
            self.player.x,
            self.player.y,
            self.player.z,
            on_ground)

    def _on_visible_player(self, entity_id, player_uuid, x, y, z, yaw, pitch):
        self.world.entities_object.entities[entity_id] = Entity(self)
        self.world.entities_object.entities[entity_id].update_option(
            entity_id=entity_id,
            UUID=player_uuid,
            x=x,
            y=y,
            z=z,
            yaw=yaw,
            pitch=pitch,
            is_player=True)

        self.on_visible_player(self.world.entities_object.entities[entity_id])

    def on_visible_player(self, entity: Entity):
        pass

    def on_entity_position_and_rotation(self,
                                        entity,
                                        delta_x=None,
                                        delta_y=None,
                                        delta_z=None,
                                        yaw=None,
                                        pitch=None,
                                        on_ground=True):
        pass

    def _on_entity_position_and_rotation(self,
                                         entity_id,
                                         delta_x=None,
                                         delta_y=None,
                                         delta_z=None,
                                         yaw=None,
                                         pitch=None,
                                         on_ground=True):
        if entity_id in self.world.entities_object.entities:
            self.world.entities_object.entities[entity_id].update_from_delta(
                x=delta_x,
                y=delta_y,
                z=delta_z)
            self.world.entities_object.entities[entity_id].update_option(
                yaw=eval([f'{yaw} / 128 * 180', 'None'][yaw is None]),
                pitch=eval([f'{pitch} / 64 * 90', 'None'][pitch is None]),
                on_ground=on_ground)

            self.on_entity_position_and_rotation(
                self.world.entities_object.entities[entity_id],
                delta_x=delta_x,
                delta_y=delta_y,
                delta_z=delta_z,
                yaw=self.world.entities_object.entities[entity_id].yaw,
                pitch=self.world.entities_object.entities[entity_id].pitch,
                on_ground=on_ground)

    def _on_entity_teleport(self, entity_id, x, y, z, yaw, pitch, on_ground):
        if entity_id in self.world.entities_object.entities:
            self.world.entities_object.entities[entity_id].update_option(
                x=x,
                y=y,
                z=z,
                yaw=yaw,
                pitch=pitch,
                on_ground=on_ground
            )

            self.on_entity_teleport(self.world.entities_object.entities[entity_id], x, y, z, yaw, pitch, on_ground)

    def on_entity_teleport(self,
                           entity,
                           x=None,
                           y=None,
                           z=None,
                           yaw=None,
                           pitch=None,
                           on_ground=None):
        pass

    @thread
    def _break_block(self, x, y, z, face, ticks):
        time.sleep(self.world.seconds_per_tick * ticks)
        self.factory.quarry_protocol.send_stop_breaking(x, y, z, face, "break")

    def break_block(self, x, y, z, face="top", ticks=0):
        face = getattr(BlockFace, face, BlockFace.TOP).value
        self.factory.quarry_protocol.send_start_breaking(x, y, z, face)
        self._break_block(x, y, z, face, ticks)

    def place_block(self,
                    x,
                    y,
                    z,
                    hand="main",
                    face="top",
                    cursor_x=.5,
                    cursor_y=.5,
                    cursor_z=.5,
                    inside_block=False):

        hand = getattr(Hand, hand, Hand.MAIN).value
        face = getattr(BlockFace, face, BlockFace.TOP).value

        for name, value in zip(('cursor_x', 'cursor_y', 'cursor_z'), (cursor_x, cursor_y, cursor_z)):
            if type(value) is str:
                locals()[name] = float(str(value).lower() in ['east', 'top', 'south'])

        self.factory.quarry_protocol.send_player_block_placement(hand, x, y, z, face, cursor_x, cursor_y, cursor_z, inside_block)

    def switch_slots(self, source: int, destination: int):

        _source_item = self.player.inventory.slots[source]
        _destination_item = self.player.inventory.slots[destination]

        # Select on the source item
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(source, _source_item, mode=0, button=0, window_id=0, action_id=1)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 1)

        self.player.inventory.slots[source] = {'item': None}
        self.player.inventory.window.held_item = _source_item

        # Place the item in the destination slot
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(destination, _destination_item, mode=0, button=0, window_id=0, action_id=2)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 2)

        self.player.inventory.slots[destination] = _source_item
        self.player.inventory.window.held_item = _destination_item

        # Place the old item of the destination slot in the source if needed
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(source, {'item': None}, mode=0, button=0, window_id=0, action_id=3)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 3)

        self.player.inventory.slots[source] = _destination_item
        self.player.inventory.window.held_item = {'item': None}

    def _on_window_confirmation(self, window_id, action_number, accepted):

        # Send "I'm sorry 'server' packet to make the server not to ignore future packets"
        if not accepted:
            self.factory.quarry_protocol.send_window_confirm(window_id, action_number, accepted)

        self.player.inventory.window.on_window_confirmation(window_id, action_number, accepted)
        self.on_window_confirmation(window_id, action_number, accepted)

    def on_window_confirmation(self, window_id, action_number, accepted):
        pass


if __name__ == '__main__':
    client = MinecraftQuarryClient("pyMClient", debug=False)
    client.join_server(address="127.0.0.1", port=25565)
