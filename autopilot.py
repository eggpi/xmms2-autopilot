import recommend

import time
import logging
import random

import xmmsclient

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

        self.load_xmms_config(self.xsync.config_list_values())

        self.xasync = xmmsclient.XMMS("autopilot-async")
        self.xasync.connect()

        self.xasync.broadcast_playlist_loaded(cb = self.on_playlist_loaded)
        self.xasync.broadcast_playlist_changed(cb = self.on_playlist_changed)
        self.xasync.broadcast_playback_current_id(cb = self.on_playback_current_id)
        self.xasync.broadcast_config_value_changed(cb = self.on_config_changed)

        self.pos_cache = None
        self.last_song_start_time = None
        self.playlist_entries_cache = self.xsync.playlist_list_entries()
        self.insertions = []

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
        logging.info("config changed, reloading")
        self.load_xmms_config(config_val.get_dict())

    def on_playlist_loaded(self, pls_val):
        pls_name = pls_val.get_string()
        logging.debug("loaded playlist '%s', updating cache", pls_name)
        self.playlist_entries_cache = self.xsync.playlist_list_entries()

    def on_playlist_changed(self, changed_val):
        changed_dict = changed_val.get_dict()

        type = changed_dict["type"]
        if type not in (xmmsclient.PLAYLIST_CHANGED_INSERT,
                        xmmsclient.PLAYLIST_CHANGED_MOVE,
                        xmmsclient.PLAYLIST_CHANGED_REMOVE):
            return True

        pos = changed_dict["position"]
        current_entries = self.xsync.playlist_list_entries()

        if type == xmmsclient.PLAYLIST_CHANGED_INSERT:
            logging.debug("insert dict: %s", changed_dict)

            mid = current_entries[pos]
            if self.check_own_insertion(pos, mid):
                logging.debug("we inserted %s, low feedback", mid)
                weight = recommend.FEEDBACK_WEIGHT_LOW
            else:
                logging.debug("user inserted %s, high feedback", mid)
                weight = recommend.FEEDBACK_WEIGHT_HIGH

            if pos > 0:
                recommend.positive(current_entries[pos-1], mid, weight)

        elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
            logging.debug("removal dict: %s", changed_dict)
            if pos > 0 and len(self.playlist_entries_cache) > pos:
                recommend.negative(self.playlist_entries_cache[pos-1],
                                   self.playlist_entries_cache[pos],
                                   recommend.FEEDBACK_WEIGHT_HIGH)

        else:
            logging.debug("move dict: %s", changed_dict)
            pos = changed_dict["newposition"]
            if pos > 0 and len(current_entries) > pos:
                recommend.positive(current_entries[pos-1],
                                   current_entries[pos])

        self.playlist_entries_cache = current_entries
        return True

    def on_playback_current_id(self, id_val):
        id = id_val.get_int()
        pos = self.xsync.playlist_current_pos()["position"]

        if pos == self.pos_cache:
            # we only care about song transitions
            return

        current_time = time.time()

        if (None not in (self.pos_cache, self.last_song_start_time) and
           current_time - self.last_song_start_time < self.FAST_SONG_CHANGE_THRESH and
           len(self.playlist_entries_cache) > pos > 1):

            logging.debug("fast song change, giving negative feedback")
            recommend.negative(self.playlist_entries_cache[self.pos_cache-1],
                               self.playlist_entries_cache[self.pos_cache],
                               recommend.FEEDBACK_WEIGHT_LOW)

        self.pos_cache = pos
        self.last_song_start_time = current_time

        next = recommend.next(id, default = self.choose_random_media())
        logging.info("requested next for %s, got %s", id, next)

        logging.info("requested next for %s, got %s", id_to_draw_next, next)
        self.do_insertion(pos+1, next)

    def choose_random_media(self):
        all_media_coll = xmmsclient.coll_parse("in:'All Media'")
        return random.choice(self.xsync.coll_query_ids(all_media_coll))

    def do_insertion(self, pos, mid):
        self.insertions.append((pos, mid))
        self.xsync.playlist_insert_id(pos, mid)

    def check_own_insertion(self, pos, mid):
        try:
            self.insertions.remove((pos, mid))
        except ValueError:
            return False

        return True

if __name__ == "__main__":
    logging.basicConfig(level = logging.DEBUG,
                        format = "%(levelname)s:%(funcName)s:%(lineno)s - "
                                 "%(message)s")

    recommend.GRAPH_DOT_FILE = "autopilot_graph.dot"
    recommend.GRAPH_PERSISTENCE_FILE = "autopilot_graph.pickle"

    autopilot = Autopilot()
