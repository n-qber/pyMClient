from twisted.internet import reactor
from quarry.net.client import ClientProtocol, ClientFactory
from quarry.net.auth import OfflineProfile, Profile
from quarry.types.buffer import Buffer1_14
from QuarryPlayer import Player, World, Entity, BlockFace, Hand, DiggingStatus, Confirmations, thread, InteractionType
from bitstring import BitStream
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

    def packet_login_disconnect(self, buff: Buffer1_14):
        super(MinecraftQuarryClientProtocol, self).packet_login_disconnect(buff)
        buff.restore()
        reason = buff.unpack_chat()
        return self.quarry_client._on_kicked(reason)

    def packet_close_window(self, buff: Buffer1_14):
        window_id = buff.unpack('B')

        self.quarry_client._on_close_window(window_id)

    def packet_respawn(self, buff: Buffer1_14):
        dimension = buff.unpack_nbt()
        world_name = buff.unpack_string()
        hashed_seed = buff.unpack('q')
        gamemode = buff.unpack('B')
        previous_gamemode = buff.unpack('B')
        is_debug = buff.unpack('?')
        is_flat = buff.unpack('?')
        copy_metadata = buff.unpack('?')

        self.quarry_client._on_packet_respawn(dimension, world_name, hashed_seed, gamemode, previous_gamemode, is_debug, is_flat, copy_metadata)

    def packet_block_break_animation(self, buff: Buffer1_14):
        entity_id = buff.unpack_varint()
        location = buff.unpack_position()
        destroy_stage = buff.unpack('b')

        self.quarry_client._on_block_break_animation(entity_id, location, destroy_stage)

    def packet_block_metadata_response(self, buff: Buffer1_14):
        transaction_id = buff.unpack_varint()
        nbt = buff.unpack_nbt()
        
        self.quarry_client._on_block_metadata_response(transaction_id, nbt)

    def packet_acknowledge_player_digging(self, buff: Buffer1_14):
        location = buff.unpack_position()
        block_state_id = buff.unpack_varint()
        status = buff.unpack_varint()
        successful = buff.unpack('?')

        self.quarry_client._on_acknowledge_player_digging(location, block_state_id, DiggingStatus(status), successful)

    def packet_tab_complete(self, buff: Buffer1_14):
        _id = buff.unpack_varint()
        start = buff.unpack_varint()
        length = buff.unpack_varint()
        count = buff.unpack_varint()

        matches = []
        for match_index in range(count):
            match = buff.unpack_string()
            has_tooltip = buff.unpack('?')
            if has_tooltip:
                tooltip = buff.unpack_chat()

            matches.append((match, None if not has_tooltip else tooltip))

        self.quarry_client._on_tab_complete(_id, start, length, matches)

    def packet_multi_block_change(self, buff: Buffer1_14):
        chunk_section_position_stream = BitStream(buff.read(8))
        chunk_x, chunk_z, chunk_y = (
            chunk_section_position_stream.read(22).int,
            chunk_section_position_stream.read(22).int,
            chunk_section_position_stream.read(20).int
        )
        buff.unpack('?')
        blocks_array_size = buff.unpack_varint()
        blocks = []
        for _ in range(blocks_array_size):
            block_varlong = BitStream('0b' + bin(buff.unpack_varint(max_bits=64))[2:].rjust(64, '0'))
            block_state_id = block_varlong.read(block_varlong.length - 12).uint
            x, z, y = block_varlong.read(4).uint, block_varlong.read(4).uint, block_varlong.read(4).uint
            blocks.append((block_state_id, (x, y, z)))
            
        self.quarry_client._on_multi_block_change(chunk_x, chunk_y, chunk_z, blocks)

    def packet_block_change(self, buff: Buffer1_14):
        x, y, z = buff.unpack_position()

        block_id = buff.unpack_varint()

        self.quarry_client._on_block_change(x, y, z, block_id)

    def packet_time_update(self, buff: Buffer1_14):
        world_age, time_of_day = buff.unpack('qq')

        self.quarry_client._on_time_update(world_age, time_of_day)

    def packet_chunk_data(self, buff: Buffer1_14):
        self.quarry_client.world.chunks.new_chunk_data(buff.read())

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

    def use_item(self, hand: Hand = 0):
        if type(hand) is not int:
            hand = hand.value
        buff = Buffer1_14()
        buff.add(buff.pack_varint(hand))

        self.send_packet('use_item', buff.read())

    def send_chat_message(self, message):
        buff = Buffer1_14()
        buff.add(buff.pack_string(message))

        self.send_packet('chat_message', buff.read())

    def swap_hands(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(DiggingStatus.SWAP_ITEM.value))
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
        player_id = buff.unpack('i')
        is_hardcore = buff.unpack('?')
        gamemode = buff.unpack('B')
        previous_gamemode = buff.unpack('b')
        world_count = buff.unpack_varint()
        world_names = []
        for _ in range(world_count):
            world_names.append(buff.unpack_string())

        dimension_codec = buff.unpack_nbt()
        dimension = buff.unpack_nbt()
        world_name = buff.unpack_string()
        hashed_seed = buff.unpack('q')
        max_players = buff.unpack_varint()
        view_distance = buff.unpack_varint()
        reduced_debug_info = buff.unpack('?')
        enable_respawn_screen = buff.unpack('?')
        is_debug = buff.unpack('?')
        is_flat = buff.unpack('?')

        self.quarry_client._on_join_game(player_id,
                                         is_hardcore,
                                         gamemode,
                                         previous_gamemode,
                                         world_names,
                                         dimension_codec,
                                         dimension,
                                         world_name,
                                         hashed_seed,
                                         max_players,
                                         view_distance,
                                         reduced_debug_info,
                                         enable_respawn_screen,
                                         is_debug,
                                         is_flat)

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

    def send_nbt_query(self, transaction_id, x, y, z):
        buff = Buffer1_14()

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
        buff.add(buff.pack_varint(DiggingStatus.SHOOT_ARROW.value))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))

        self.send_packet('player_digging', buff.read())

    def drop_item(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(DiggingStatus.DROP_ITEM.value))
        buff.add(buff.pack_position(0, 0, 0))
        buff.add(buff.pack('B', 0))

        self.send_packet('player_digging', buff.read())

    def drop_stack(self):
        buff = Buffer1_14()
        buff.add(buff.pack_varint(DiggingStatus.DROP_ITEM_STACK.value))
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
        buff.add(buff.pack_varint(DiggingStatus.START_DIGGING.value))
        buff.add(buff.pack_position(x, y, z))
        buff.add(buff.pack('B', face))

        self.send_packet('player_digging', buff.read())

    def send_stop_breaking(self, x, y, z, face, operation="break"):
        status = {
            'cancel': DiggingStatus.CANCEL_DIGGING,
            'break': DiggingStatus.FINISH_DIGGING
        }.get(operation, DiggingStatus.FINISH_DIGGING)
        buff = Buffer1_14()
        buff.add(buff.pack_varint(status.value))
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

    def send_entity_action(self, entity_id, action_id, jump_boost: int = 0):
        buff = Buffer1_14()
        buff.add(
            buff.pack_varint(entity_id) +
            buff.pack_varint(action_id) +
            buff.pack_varint(jump_boost)
        )

        self.send_packet('entity_action', buff.read())

    def send_confirm_transaction(self, window_id, action_number, accepted):
        buff = Buffer1_14()
        buff.add(buff.pack('bh?', window_id, action_number, accepted))

        self.send_packet('confirm_transaction', buff.read())

    def send_tab_complete(self, transaction_id, text):
        buff = Buffer1_14()

        buff.add(
            buff.pack_varint(transaction_id) +
            buff.pack_string(text)
        )

        self.send_packet('tab_complete', buff.read())

    def send_block_metadata_request(self, transaction_id, location):
        buff = Buffer1_14()

        buff.add(
            buff.pack_varint(transaction_id) +
            buff.pack_position(*location)
        )

        self.send_packet('block_metadata_request', buff.read())

    def send_interact_entity(self,
                             entity_id,
                             action_type,
                             target_x=None,
                             target_y=None,
                             target_z=None,
                             hand=0,
                             sneaking=False):

        if type(action_type) is str:
            action_type: InteractionType = getattr(InteractionType, action_type, InteractionType.INTERACT)

        buff = Buffer1_14()
        buff.add(
            buff.pack_varint(entity_id) +
            buff.pack_varint(action_type.value) +
            ((buff.pack('fff', target_x, target_y, target_z) + buff.pack_varint(int(hand))) if action_type == InteractionType.INTERACT_AT else b'') +
            buff.pack('?', sneaking)
        )

        self.send_packet('use_entity', buff.read())


class MinecraftQuarryClient:
    def __init__(self,
                 username: str,
                 email: str = "",
                 password: str = "",
                 humanized: bool = True,
                 debug: bool = False):

        self.confirmations = Confirmations(self)
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

    def send_tab_complete(self, _id, text):
        self.factory.quarry_protocol.send_tab_complete(_id, text)

    def send_chat_message(self, message):
        self.factory.quarry_protocol.send_chat_message(message)

    def use_item(self, hand="main"):

        if type(hand) is str:
            hand = getattr(Hand, hand.upper(), Hand.MAIN)

        self.factory.quarry_protocol.use_item(hand)

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

    def _on_player_position(self, x, y, z, on_ground):
        self.player.x = x
        self.player.y = y
        self.player.z = z
        self.player.on_ground = on_ground
        return self.on_player_position(x, y, z, on_ground)

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

    def start_breaking_block(self, x, y, z, face="top"):
        face = getattr(BlockFace, face, BlockFace.TOP).value
        self.factory.quarry_protocol.send_start_breaking(x, y, z, face)

    def stop_breaking_block(self, x, y, z, face="top", operation="break"):
        face = getattr(BlockFace, face, BlockFace.TOP).value
        self.factory.quarry_protocol.send_stop_breaking(x, y, z, face, operation=operation)

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

        # Select on the source item
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(source, self.player.inventory.slots[source], mode=0, button=0, window_id=0, action_id=1)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 1)

        self.player.inventory.window.held_item, self.player.inventory.slots[source] =\
            self.player.inventory.slots[source], self.player.inventory.window.held_item

        # Place the item in the destination slot
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(destination, self.player.inventory.slots[destination], mode=0, button=0, window_id=0, action_id=2)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 2)

        self.player.inventory.window.held_item, self.player.inventory.slots[destination] =\
            self.player.inventory.slots[destination], self.player.inventory.window.held_item

        # Place the old item of the destination slot in the source if needed
        _status = False
        while not _status:
            self.factory.quarry_protocol.send_click_window(source, self.player.inventory.slots[source], mode=0, button=0, window_id=0, action_id=3)

            # 1.17+ does not need a confirmation from the server
            if self.factory.quarry_protocol.protocol_version >= 755:
                break

            _status = self.player.inventory.window.wait_action_id(0, 3)

        self.player.inventory.window.held_item, self.player.inventory.slots[source] =\
            self.player.inventory.slots[source], self.player.inventory.window.held_item

    def _on_window_confirmation(self, window_id, action_number, accepted):

        # Send "I'm sorry 'server' packet to make the server not to ignore future packets"
        if not accepted:
            self.factory.quarry_protocol.send_window_confirm(window_id, action_number, accepted)

        self.player.inventory.window.on_window_confirmation(window_id, action_number, accepted)
        self.on_window_confirmation(window_id, action_number, accepted)

    def on_window_confirmation(self, window_id, action_number, accepted):
        pass

    def _on_block_change(self, x, y, z, block_id):
        self.world.chunks.new_block_change(x, y, z, block_id)
        self.on_block_change(x, y, z, block_id)

    def on_block_change(self, x, y, z, block_id):
        pass

    def on_player_position(self, x, y, z, on_ground):
        pass

    def _on_time_update(self, world_age, time_of_day):
        self.world.age = world_age
        self.world.time_of_day = time_of_day % 24000

        self.on_time_update(self.world.age, self.world.time_of_day, self.world.day_state)

    def on_time_update(self, world_age, time_of_day, day_state):
        pass

    def _on_tab_complete(self, _id, start, length, matches):
        self.on_tab_complete(_id, start, length, matches)

    def on_tab_complete(self, _id, start, length, matches):
        pass

    def start_sneaking(self):
        self.factory.quarry_protocol.send_entity_action(
            self.player.entity_id, 0  # start sneaking ID
        )

    def stop_sneaking(self):
        self.factory.quarry_protocol.send_entity_action(
            self.player.entity_id, 1,  # stop sneaking ID
        )

    def _on_acknowledge_player_digging(self, location, block_state_id, status, successful):
        self.on_acknowledge_player_digging(location, block_state_id, status, successful)

    def on_acknowledge_player_digging(self, location, block_state_id, status, successful):
        pass

    def _on_block_metadata_response(self, transaction_id, nbt):
        self.on_block_metadata_response(transaction_id, nbt)

    def on_block_metadata_response(self, transaction_id, nbt):
        pass

    def request_block_metadata(self, x, y, z, transaction_id=0):
        self.factory.quarry_protocol.send_block_metadata_request(transaction_id, (x, y, z))

    def _on_block_break_animation(self, entity_id, location, destroy_stage):
        self.on_block_break_animation(entity_id, location, destroy_stage)

    def on_block_break_animation(self, entity_id, location, destroy_stage):
        pass

    def _on_packet_respawn(self, dimension, world_name, hashed_seed, gamemode, previous_gamemode, is_debug, is_flat,
                           copy_metadata):
        self.world.dimension = dimension
        self.world.name = world_name
        self.world.hashed_seed = hashed_seed
        self.world.is_debug = is_debug
        self.world.is_flat = is_flat
        self.player.inventory.clear()

        self.player.gamemode = gamemode

        self.on_packet_respawn(dimension, world_name, hashed_seed, gamemode, previous_gamemode, is_debug, is_flat,
                           copy_metadata)

    def on_packet_respawn(self, dimension, world_name, hashed_seed, gamemode, previous_gamemode, is_debug, is_flat,
                          copy_metadata):
        pass

    def _on_join_game(self, player_id, is_hardcore, gamemode, previous_gamemode, world_names, dimension_codec, dimension,
                      world_name, hashed_seed, max_players, view_distance, reduced_debug_info, enable_respawn_screen,
                      is_debug, is_flat):

        self.player.player_id = self.player.entity_id = player_id
        self.player.gamemode = gamemode
        self.world.name = world_name
        self.world.dimension = dimension
        self.world.hashed_seed = hashed_seed
        self.world.max_players = max_players
        self.world.is_debug = is_debug
        self.world.is_flat = is_flat

        self.on_join_game(player_id, is_hardcore, gamemode, previous_gamemode, world_names, dimension_codec, dimension,
                      world_name, hashed_seed, max_players, view_distance, reduced_debug_info, enable_respawn_screen,
                      is_debug, is_flat)

    def on_join_game(self, player_id, is_hardoce, gamemode, previous_gamemode, world_names, dimension_codec, dimension,
                     world_name, hashed_seed, max_players, view_distance, reduced_debug_info, enable_respawn_screen,
                     is_debug, is_flat):
        pass

    def _on_close_window(self, window_id):
        self.player.inventory.window.id = 0

    def _on_kicked(self, reason):
        self.on_kicked(reason)

    def on_kicked(self, reason):
        pass

    def _on_multi_block_change(self, chunk_x, chunk_y, chunk_z, blocks):
        self.world.chunks.new_multi_block_change(chunk_x, chunk_y, chunk_z, blocks)
        self.on_multi_block_change(chunk_x, chunk_y, chunk_z, blocks)

    def on_multi_block_change(self, chunk_x, chunk_y, chunk_z, blocks):
        pass

    def interact_with(self,
                      entity_id,
                      action="interact",
                      target_position=(None, None, None),
                      hand=None,
                      sneaking=None):

        if sneaking is None:
            sneaking = self.player.sneaking

        action = action if type(action) is not str else getattr(InteractionType, action.upper(), InteractionType.INTERACT)

        if action == InteractionType.INTERACT_AT:
            assert target_position != (None, None, None), "Need [target_position] when using [interact_at] action"

        if hand is None:
            hand = Hand.MAIN

        self.factory.quarry_protocol.send_interact_entity(entity_id, action, *target_position, hand, sneaking)

    def eat(self, hand="main"):
        self.confirmations.update_health.status  # clearing the status variable
        self.use_item(hand)
        while not self.confirmations.update_health.status:
            time.sleep(self.world.seconds_per_tick)
        self.factory.quarry_protocol.update_held_item()


if __name__ == '__main__':
    client = MinecraftQuarryClient("pyMClient", debug=False)
    client.join_server(address="127.0.0.1", port=25565)
