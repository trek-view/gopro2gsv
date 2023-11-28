from collections import UserDict
from haversine import haversine, Unit
import math
from geographiclib.geodesic import Geodesic

class metadata_dict(UserDict):
    def __init__(self, **kw):
        self.key_values = []
        super().__init__(**kw)

    def __getitem__(self, key) -> str:
        value = super().__getitem__(key)
        if isinstance(value, list):
            return value[0]
        return value

    def __setitem__(self, key, item):
        self.key_values.append((key, item))
        v = self.list(key)
        v.append(item)
        super().__setitem__(key, v)
    
    def list(self, key):
        try:
            return super().__getitem__(key)
        except KeyError as e:
            return []

    def get_track_info(self, trackid, key):
        pass

def calculateVelocities(start, end, time_diff):
    end_latitude, end_longitude, end_altitude = map(float, end)
    start_latitude, start_longitude, start_altitude = map(float, start)
    distance = haversine((start_latitude, start_longitude), (end_latitude, end_longitude), Unit.METERS)

    brng = Geodesic.WGS84.Inverse(start_latitude, start_longitude, end_latitude, end_longitude)
    azimuth1 = (brng['azi1'] + 360) % 360
    azimuth2 = (brng['azi2'] + 360) % 360
    AC = math.sin(math.radians(azimuth1))*distance
    BC = math.cos(math.radians(azimuth2))*distance
    alt = end_altitude - start_altitude
    if time_diff > 0:
        v_east = AC/time_diff
        v_north = BC/time_diff
        v_up = alt/time_diff
        v = distance/time_diff
    else:
        v_east = 0.5
        v_north = 0.5
        v_up = 0
        v = 0.707
    return v, (v_east, v_north, v_up)