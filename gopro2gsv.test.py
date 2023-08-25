from src.__main__ import main, parse_args
from types import SimpleNamespace
import pathlib
from pathlib import PosixPath, Path

args, is_photo_mode = (SimpleNamespace(input_video=None, input_directory=pathlib.PosixPath('/home/fqrious/tmp/fus-360-pho-002s6'), video_telemetry_format='GPMD', watermark=None, path_to_nadir="stock_nadirs/trek-view-circle-nadir.png", output_filepath="/home/fqrious/tmp/fus/fuslie", upload_to_streetview=False), True)
# args, is_photo_mode = (SimpleNamespace(input_video=None, input_directory=pathlib.PosixPath('/home/fqrious/tmp/fus-360-pho-002s6'), video_telemetry_format='GPMD', path_to_nadir=None, watermark="stock_nadirs/trek-view-circle-nadir.png", output_filepath="/home/fqrious/tmp/fus/fuslie", upload_to_streetview=False), True)
# args, is_photo_mode = (SimpleNamespace(input_video=pathlib.PosixPath('/home/fqrious/Downloads/GS018423.360'), path_to_nadir=None, output_filepath="/home/fqrious/tmp/fus/fuslie", upload_to_streetview=False), False)
# args, is_photo_mode = (SimpleNamespace(input_video=pathlib.PosixPath('/home/fqrious/tmp/fus/fuslie-0.mp4'), path_to_nadir=None, output_filepath="/home/fqrious/tmp/fus/fuslie", upload_to_streetview=False), False)

main(args, is_photo_mode)


if __name__ == '__main__':
    video = Path('/home/fqrious/tmp/fus/fuslie-0_watermarked.mp4')
    gsv = GSV('703153271591-lusbgebq1r5iop5ukl1ahkldcvc5smjh.apps.googleusercontent.com', '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')
    # print("upload url:", gsv.get_upload_url())
    print(gsv.upload_video(video))