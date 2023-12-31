import sqlite3, os, json, sys
from pathlib import Path
from datetime import date, datetime

from logging import getLogger
logger = getLogger(__name__)
DEFAULT_PATH = "gopro2gsv.sqlite"

def json_serialize(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def get_timelapse_tuple(pk, meta:dict) -> tuple:
    return (
        pk,
        json.dumps(meta, default=json_serialize), #photo_data
        str(meta['path']),
        str(meta.get('newpath', "")) or None,
        meta.get('error'),
    )

class DB:
    db_path : Path
    def __init__(self, db_path=None):
        if not db_path:
            db_path = DEFAULT_PATH
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self):
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create UserAuth table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS GSVAuth (
                    user_id INTEGER PRIMARY KEY,
                    auth_json TEXT,
                    UNIQUE (user_id)
                )
            ''')

            # Create Video table
            cursor.execute('''
                CREATE TABLE Video (
                    id INTEGER PRIMARY KEY,
                    type    TEXT,
                    cmdline TEXT,
                    input_path TEXT,
                    final_path TEXT,
                    gpx_file   TEXT,
                    log_path   TEXT,
                    streetview_id TEXT,
                    gsv_status TEXT,
                    gsv_error TEXT
                )
            ''')


            # Create Photos table
            cursor.execute('''
                CREATE TABLE Photos (
                    id INTEGER PRIMARY KEY,
                    timelapse_video_id INTEGER,
                    original_path TEXT,
                    final_path TEXT,
                    error TEXT,
                    photo_data TEXT,
                    FOREIGN KEY(timelapse_video_id) REFERENCES Video(id)
                )
            ''')

            conn.commit()
            conn.close()

    def insert_output(self, input_path: Path, final_path: Path, log_path: Path, streetview_id=None, is_photo_mode=True, video_info={}):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        type = "VIDEO"
        if is_photo_mode:
            type = "TIMELAPSE"
        gsv_status = None
        if streetview_id:
            gsv_status = "PROCESSING"
        cursor.execute(f'''
            INSERT INTO Video (cmdline, type, input_path, final_path, streetview_id, gsv_status, log_path, gpx_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (json.dumps(sys.argv), type, str(input_path), str(final_path), streetview_id, gsv_status, str(log_path), video_info.get("gpx_file")))
        conn.commit()
        pk = cursor.lastrowid
        conn.close()

        if is_photo_mode:
            self.record_timelapse(video_info["images"], pk)
        return pk

    def record_timelapse(self, images, pk=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(f'''
            INSERT INTO Photos (timelapse_video_id, photo_data, original_path, final_path, error)
            VALUES (?, ?, ?, ?, ?)
        ''', map(lambda x:get_timelapse_tuple(pk, x), images))

        conn.commit()
        conn.close()
        return

    def insert_user_setting(self, user_id, setting_name, setting_value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO UserSettings (user_id, setting_name, setting_value)
            VALUES (?, ?, ?)
        ''', (user_id, setting_name, setting_value))
        conn.commit()
        conn.close()


    def save_gsv_auth(self, creds: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Insert user authentication data
        user_id = 0
        cursor.execute('''
            INSERT OR REPLACE INTO GsvAuth (user_id, auth_json)
            VALUES (?, ?)
        ''', (user_id, creds))
        conn.commit()
        conn.close()


    def get_gsv_auth(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            user_id = 0
            cursor.execute('SELECT auth_json FROM GsvAuth WHERE user_id = ?', (user_id,))
            settings = cursor.fetchone()
            conn.close()
            return json.loads(settings[0])
        except:
            return None

    def get_unfinished_gsv_uploads(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT streetview_id, gsv_status, gsv_error FROM Video WHERE gsv_status = ?', ("PROCESSING",))
            uploads = cursor.fetchall()
            conn.close()
            return uploads
        except:
            raise
    
    def update_gsv_statuses(self, statuses: list[tuple[str, str, str]]):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany('''
                UPDATE Video 
                SET gsv_status = ?, gsv_error = ?
                WHERE streetview_id = ?''', statuses)
            conn.commit()
            conn.close()
            return True
        except:
            raise
    
    # Similar functions for inserting data into other tables
