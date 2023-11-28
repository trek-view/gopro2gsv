# Test cases

Test cases for gopro2gsv.

Download the test cases here: https://drive.google.com/drive/folders/1O1T8CR8BOBb8bfVixoPfOojhPqXUrz23?usp=drive_link

## Mode 1 (equirectangular mp4 video -> final video)

### Test inputs

#### Non-Equi video

GH018678.MP4

#### Equi video

GS016843.mp4 = 00:03:07 (187 secs) duration

```shell
exiftool -ee -p gpx.fmt tests/ski/GS016843.mp4 > tests/ski/GS016843.gpx
```

### Validations

```shell
python3 gopro2gsv.py \
	--input_video tests/hero_videos/GH018678.MP4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/mode1/test0/GH018678.MP4
```

### No frame extraction, add a nadir with default size (25%)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/mode1/test1/GS016843.mp4
```

### No frame extraction, add a nadir with custom size (10%)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--size_of_nadir 10 \
	--output_filepath tests/output/mode1/test2/GS016843.mp4
```

## Mode 2 (equirectangular timelapse frames -> final video)



## Mode 2 (equirectangular mp4 video -> timelapse frames -> final video)

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

## Mode 2

