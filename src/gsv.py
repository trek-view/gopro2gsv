
from logging import getLogger
logger = getLogger(__name__)
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper
import requests, os, json
import urllib.parse as urlparse
from .errors import FatalException

from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient import errors as google_errors
from google.oauth2.credentials import Credentials
from google_auth_oauthlib import get_user_credentials

def get_file_size(file: Path):
  """Returns the size of the file."""
  with file.open("rb") as fh:
    fh.seek(0, os.SEEK_END)
    return fh.tell()


def do_upload(url, file: Path, file_size: int, method="PUT", headers={}):
    try:
        with file.open("rb") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                wrapped_file = CallbackIOWrapper(t.update, f, "read")
                resp = requests.request(method, url, data=wrapped_file, headers=headers)
                resp.raise_for_status()
                return resp
    except Exception as e:
        raise FatalException(f"An error occured while uploading {file} to {url}") from e

class GSV:
    SCOPES = ["https://www.googleapis.com/auth/streetviewpublish"]
    API_NAME = "streetviewpublish"
    API_VERSION = "v1"
    credentials: Credentials = None

    def __init__(self, client_id, client_secret, creds_info=None):
        if creds_info:
            self.credentials = Credentials.from_authorized_user_info(creds_info, self.SCOPES)
            if not self.credentials.valid:
                client_id = self.credentials.client_id
                client_secret = self.credentials.client_secret
        if not self.credentials:
            self.credentials = get_user_credentials(self.SCOPES, client_id, client_secret)

    def upload_headers(self, filesize):
        return {
            "Content-Type": "video/mp4",
            "Authorization": "Bearer " + self.credentials.token,
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-Content-Length": str(filesize),
        }

    def get_upload_url(self):
        service = build(self.API_NAME, self.API_VERSION, credentials=self.credentials)
        resp = service.photoSequence().startUpload(body={}).execute()
        upload_url = str(resp["uploadUrl"])
        return upload_url

    def upload_video(self, video: Path):
        upload_url = self.get_upload_url()
        size       = get_file_size(video)
        upload     = do_upload(upload_url, video, size, "POST", headers=self.upload_headers(size))
        name = self.publish(upload_url, video.name)
        return upload, name

    def publish(self, upload_url, filename):
        service = build(self.API_NAME, self.API_VERSION, credentials=self.credentials)
        publish_payload = {"uploadReference": {"uploadUrl": upload_url}, "filename": filename}
        try:
            resp = service.photoSequence().create(body=publish_payload, inputType="VIDEO").execute()
            return resp["name"]
        except google_errors.HttpError as e:
            msg = json.loads(e.content)
            raise FatalException(f"Publish failed with message: {msg}") from e


