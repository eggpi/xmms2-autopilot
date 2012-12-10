import recommend

import time
import logging

import xmmsclient

FAST_SONG_CHANGE_THRESH = 5 # seconds

class Autopilot(object):
    def __init__(self):
        self.xsync = xmmsclient.XMMSSync("autopilot-sync")
        self.xsync.connect()

        self.xasync = xmmsclient.XMMS("autopilot-async")
        self.xasync.connect()

        self.xasync.broadcast_playlist_loaded(cb = self.on_playlist_loaded)
        self.xasync.broadcast_playlist_changed(cb = self.on_playlist_changed)
        self.xasync.broadcast_playback_current_id(cb = self.on_playback_current_id)

        self.pos_cache = None
        self.last_song_start_time = None
        self.playlist_entries_cache = self.xsync.playlist_list_entries()

        logging.info("autopilot setup, starting mainloop")
        self.xasync.loop()

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
            if pos > 0 and len(current_entries) > pos:
                recommend.positive(current_entries[pos-1],
                                   current_entries[pos])

        elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
            logging.debug("removal dict: %s", changed_dict)
            if pos > 0 and len(self.playlist_entries_cache) > pos:
                recommend.negative(self.playlist_entries_cache[pos-1],
                                   self.playlist_entries_cache[pos])

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
           current_time - self.last_song_start_time < FAST_SONG_CHANGE_THRESH and
           len(self.playlist_entries_cache) > pos > 1):

            logging.debug("fast song change, giving negative feedback")
            recommend.negative(self.playlist_entries_cache[self.pos_cache-2],
                               self.playlist_entries_cache[self.pos_cache-1])

        self.pos_cache = pos
        self.last_song_start_time = current_time

        next = recommend.next(id)
        logging.info("requested next for %s, got %s", id, next)

        if next is not None:
            self.xsync.playlist_insert_id(pos+1, next)

if __name__ == "__main__":
    logging.basicConfig(level = logging.DEBUG,
                        format = "%(levelname)s:%(funcName)s:%(lineno)s - "
                                 "%(message)s")

    recommend.GRAPH_DOT_FILE = "autopilot_graph.dot"
    recommend.GRAPH_PERSISTENCE_FILE = "autopilot_graph.pickle"

    autopilot = Autopilot()
