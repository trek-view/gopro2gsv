from src.__main__ import main, parse_args
from dotenv import load_dotenv

load_dotenv()
main(*parse_args())