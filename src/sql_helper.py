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
                    cmdline TEXT,
                    input_path TEXT,
                    final_path TEXT,
                    log_path TEXT,
                    streetview_info TEXT
                )
            ''')

            # Create TimelapseImages table
            cursor.execute('''
                CREATE TABLE TimelapseImage (
                    id INTEGER PRIMARY KEY,
                    cmdline TEXT,
                    input_path TEXT,
                    final_path TEXT,
                    log_path TEXT,
                    streetview_info TEXT
                )
            ''')

            # Create Photos table
            cursor.execute('''
                CREATE TABLE Photos (
                    id INTEGER PRIMARY KEY,
                    timelapse_image_id INTEGER,
                    photo_data TEXT,
                    FOREIGN KEY(timelapse_image_id) REFERENCES TimelapseImage(id)
                )
            ''')

            conn.commit()
            conn.close()

    def insert_output(self, input_path: Path, final_path: Path, log_path: Path, streetview_info=None, is_photo_mode=True, images=[]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        table = "Video"
        if is_photo_mode:
            table = "TimelapseImage"
        cursor.execute(f'''
            INSERT INTO {table} (cmdline, input_path, final_path, streetview_info, log_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (json.dumps(sys.argv), str(input_path), str(final_path), streetview_info, str(log_path)))
        conn.commit()
        pk = cursor.lastrowid
        if is_photo_mode:
            cursor.executemany(f'''
                INSERT INTO Photos (timelapse_image_id, photo_data)
                VALUES (?, ?)
            ''', map(lambda meta: (pk, json.dumps(meta, default=json_serialize)), images))

        conn.commit()
        conn.close()
        return pk

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

    

    # Similar functions for inserting data into other tables
