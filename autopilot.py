import recommend

import xmmsclient

import argparse
import collections
import logging
import random
import time

# FIXME outdated bindings
xmmsclient.PLAYLIST_CHANGED_REPLACE = 8

class Autopilot(object):
    FAST_SONG_CHANGE_THRESH = 20 # seconds

    def __init__(self):
        self.xsync = xmmsclient.XMMSSync("autopilot-sync")
        self.xsync.connect()

        self.xmms_config_keys = {} # xmms config key -> setter
        self.register_attr_as_xmms_config(self, "FAST_SONG_CHANGE_THRESH")
        self.register_attr_as_xmms_config(recommend, "MIN_GRAPH_SIZE")
        self.register_attr_as_xmms_config(recommend, "MIN_CANDIDATES")
        self.register_attr_as_xmms_config(recommend, "MAX_CANDIDATE_DIST")
        self.register_attr_as_xmms_config(recommend, "MAX_OUT_DEGREE")
        self.register_attr_as_xmms_config(recommend, "MAX_IN_DEGREE")
        self.register_attr_as_xmms_config(recommend, "FEEDBACK_WEIGHT_HIGH")
        self.register_attr_as_xmms_config(recommend, "FEEDBACK_WEIGHT_LOW")

        self.load_xmms_config(self.xsync.config_list_values())

        self.xasync = xmmsclient.XMMS("autopilot-async")
        self.xasync.connect()

        self.reset_playlist_cache()
        self.xasync.broadcast_playlist_loaded(cb = self.on_playlist_loaded)
        self.xasync.broadcast_playlist_changed(cb = self.on_playlist_changed)
        self.xasync.broadcast_playlist_current_pos(cb = self.on_current_pos)
        self.xasync.broadcast_playback_current_id(cb = self.on_current_id)
        self.xasync.broadcast_config_value_changed(cb = self.on_config_changed)

        logging.info("autopilot setup, starting mainloop")
        self.xasync.loop()

    def register_attr_as_xmms_config(self, obj, attr):
        default = getattr(obj, attr)
        original_type = type(default) # need to convert back from str
        key = "autopilot." + attr.lower()

        xmms_config_key = self.xsync.config_register_value(key, str(default))
        self.xmms_config_keys[xmms_config_key] = \
                lambda v: setattr(obj, attr, original_type(v))

    def load_xmms_config(self, xmms_config):
        for key, setter in self.xmms_config_keys.items():
            if key in xmms_config:
                logging.info("loaded config '%s': %s", key, xmms_config[key])
                setter(xmms_config[key])

    def on_config_changed(self, config_val):
        self.load_xmms_config(config_val.get_dict())

    def on_playlist_loaded(self, pls_val):
        self.reset_playlist_cache()

    def on_current_pos(self, pos_val):
        self.fill_playlist()

    def on_current_id(self, id_val):
        current_time = time.time()
        playtime = time.time() - self.last_song_start_time
        if (playtime < self.FAST_SONG_CHANGE_THRESH and
            len(self.last_mids) == 2):

            logging.debug("fast song change, giving negative feedback")
            recommend.negative(self.last_mids[-2], self.last_mids[-1],
                               recommend.FEEDBACK_WEIGHT_LOW)

            id_to_draw_next = self.last_mids[0]
        else:
            id_to_draw_next = id_val.get_int()

        self.last_mids.append(id_val.get_int())
        self.last_song_start_time = current_time
        self.fill_playlist(id_to_draw_next)

        return True

    def on_playlist_changed(self, changed_val):
        changed_dict = changed_val.get_dict()

        type = changed_dict["type"]
        if type not in (xmmsclient.PLAYLIST_CHANGED_INSERT,
                        xmmsclient.PLAYLIST_CHANGED_MOVE,
                        xmmsclient.PLAYLIST_CHANGED_REMOVE,
                        xmmsclient.PLAYLIST_CHANGED_REPLACE):
            return True

        if type == xmmsclient.PLAYLIST_CHANGED_REPLACE:
            logging.debug("playlist replaced, resetting")

            self.reset_playlist_cache()
            return True

        pos = changed_dict["position"]
        mid = changed_dict["id"]
        if type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
            logging.debug("removal dict: %s", changed_dict)

            if pos > 0:
                recommend.negative(self.playlist_entries_cache[pos-1],
                                   self.playlist_entries_cache[pos],
                                   recommend.FEEDBACK_WEIGHT_HIGH)
            del self.playlist_entries_cache[pos]

        elif type == xmmsclient.PLAYLIST_CHANGED_INSERT:
            logging.debug("insert dict: %s", changed_dict)

            if self.check_own_insertion(pos, mid):
                weight = recommend.FEEDBACK_WEIGHT_LOW
            else:
                weight = recommend.FEEDBACK_WEIGHT_HIGH

            if pos > 0:
                recommend.positive(self.playlist_entries_cache[pos-1],
                                   mid, weight)

            self.playlist_entries_cache.insert(pos, mid)

        elif type == xmmsclient.PLAYLIST_CHANGED_MOVE:
            logging.debug("move dict: %s", changed_dict)

            newpos = changed_dict["newposition"]
            del self.playlist_entries_cache[pos]
            self.playlist_entries_cache.insert(newpos, mid)

            if newpos > 0:
                recommend.positive(self.playlist_entries_cache[newpos-1],
                                   self.playlist_entries_cache[newpos])

        self.fill_playlist()
        return True

    def choose_random_media(self):
        all_media_coll = xmmsclient.coll_parse("in:'All Media'")
        return random.choice(self.xsync.coll_query_ids(all_media_coll))

    def fill_playlist(self, id_to_draw_next = None):
        try:
            curr_pos = self.xsync.playlist_current_pos()["position"]
            if curr_pos == -1:
                return
        except xmmsclient.XMMSError:
            return

        playlist_entries = self.xsync.playlist_list_entries()

        if id_to_draw_next is None:
            id_to_draw_next = playlist_entries[curr_pos]

        if curr_pos == len(playlist_entries)-1:
            next = recommend.next(id_to_draw_next,
                                  default = self.choose_random_media())

            logging.info("next(%s) -> %s", id_to_draw_next, next)
            self.do_insertion(curr_pos+1, next)

    def do_insertion(self, pos, mid):
        self.insertions.append((pos, mid))
        self.xsync.playlist_insert_id(pos, mid)

    def check_own_insertion(self, pos, mid):
        try:
            self.insertions.remove((pos, mid))
        except ValueError:
            return False

        return True

    def reset_playlist_cache(self):
        self.insertions = []
        self.last_song_start_time = 0
        self.last_mids = collections.deque(maxlen = 2)
        self.playlist_entries_cache = self.xsync.playlist_list_entries()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--loglevel",
                        type = str,
                        choices = ("DEBUG", "INFO"),
                        default = "INFO")

    args = parser.parse_args()
    logging.basicConfig(level = getattr(logging, args.loglevel),
                        format = "%(levelname)s:%(funcName)s:%(lineno)s - "
                                 "%(message)s")

    recommend.GRAPH_DOT_FILE = "autopilot_graph.dot"
    recommend.GRAPH_PERSISTENCE_FILE = "autopilot_graph.pickle"

    autopilot = Autopilot()
