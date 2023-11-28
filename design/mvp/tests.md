# Test cases

Test cases for gopro2gsv

## Video mode (single mp4) -> Video output

GS016843.mp4 = 00:03:07 (187 secs) duration

### No frame extraction, add a nadir

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/test1/GS016843.mp4
```

## Video mode (single mp4) -> Image mode -> Video output

### Extract frames from video input at 0.5 FPS and rebuild video with normal length (300 frames)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--extract_fps 0.5 \
	--keep_extracted_frames \
	--output_filepath tests/output/test2/GS016843.mp4
```

187 * 0.5 = 93.5 (94) frames = 94 / 5 = 18.8 seconds final output

See image metadata:

```shell
exiftool tests/output/GS016843-test2-images/FRAME-00001.jpg # 2023:03:02 08:13:00.904Z
exiftool tests/output/GS016843-test2-images/FRAME-00002.jpg # 2023:03:02 08:13:01.020470999Z
exiftool tests/output/GS016843-test2-images/FRAME-00003.jpg # 2023:03:02 08:13:01.136942Z
exiftool tests/output/GS016843-test2-images/FRAME-00003.jpg # 2023:03:02 08:13:01.253413Z
```

## Video mode (single mp4) -> Image mode -> Video output

### Extract frames from video input at 0.5 FPS and rebuild video with 20 second max (100 frames)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--extract_fps 2 \
	--max_output_video_secs 20 \
	--output_filepath tests/output/test3/GS016843.mp4
```

187 * 2 = 374 frames = 375 / 5 = 75 seconds final output. Thus expect 4 videos output.
