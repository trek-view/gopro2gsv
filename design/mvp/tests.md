# Test cases

Test cases for gopro2gsv.

Download the test cases here: https://drive.google.com/drive/folders/1O1T8CR8BOBb8bfVixoPfOojhPqXUrz23?usp=drive_link

=========

## Mode 1 (equirectangular mp4 video -> final video)

=========

### Test inputs

#### Non-Equi video

GH018678.MP4

#### Equi video

GS016843.mp4 = 00:03:07 (187 secs) duration

```shell
exiftool -ee -p gpx.fmt tests/ski/GS016843.mp4 > tests/ski/GS016843.gpx
```

### Validations

Bad case:

```shell
python3 gopro2gsv.py \
	--input_video tests/hero_videos/GH018678.MP4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/mode1/test0/GH018678
```

### No frame extraction, add a nadir with default size (25%)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/mode1/test1/GS016843
```

### No frame extraction, add a nadir with custom size (10%)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--size_of_nadir 10 \
	--output_filepath tests/output/mode1/test2/GS016843
```

=========

## Mode 2 (equirectangular timelapse frames -> final video)

=========

### Validations

Bad case:

```shell
python3 gopro2gsv.py \
	--input_directory tests/hero_photos/ \
	--output_filepath tests/output/mode2/test1/hero_photos.mp4
```

### Testing smoothing with two bad GPS points (with custom value 20m/s set)

A note on how to corrupt GPS (for this test case smoothing)

```shell
exiftool -overwrite_original -GPSLatitude=40.6892 -GPSLatitudeRef=N -GPSLongitude=-74.0445 -GPSLongitudeRef=W -GPSAltitude=10 -GPSAltitudeRef="Above Sea Level" tests/UKHB001v205-some-bad-gps/GSAA7186.JPG
exiftool -overwrite_original -GPSLatitude=20.1 -GPSLatitudeRef=N -GPSLongitude=-60.1 -GPSLongitudeRef=W -GPSAltitude=10 -GPSAltitudeRef="Above Sea Level" tests/UKHB001v205-some-bad-gps/GSAA7196.JPG
```

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-some-bad-gps/ \
	--outlier_speed_meters_sec 20 \
	--output_filepath tests/output/mode2/test1A/UKHB001v205-some-bad-gps
```

Directory has 63 items. 2 are bad, so 61. 61/5= 12.2 seconds of footage

### Testing smoothing with two bad GPS points (with custom value 20m/s set) but should not process

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-some-bad-gps-not-enough/ \
	--outlier_speed_meters_sec 20 \
	--output_filepath tests/output/mode2/test1B/UKHB001v205-some-bad-gps-not-enough
```

Directory has 63 items. 2 are bad, so 18. Not enough for validation.

### Testing maximum output video length (simple)

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-frames-removed/ \
	--max_output_video_secs 20 \
	--output_filepath tests/output/mode2/test2/UKHB001v205-frames-removed
```

Directory has 590 items. 590/5 (fixed frame rate packer) = 118 seconds of footage. 118/20 = 5.9 videos. The first five 00:00:20 long. The last (sixth) 00:00:18 long.

### Testing maximum output video length (where min frame per vid should be considered)

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-frames-removed/ \
	--max_output_video_secs 13 \
	--output_filepath tests/output/mode2/test3/UKHB001v205-frames-removed
```

Directory has 590 items. 590/5 = 118 seconds of footage. 118 / 13 = 9.08 videos. Expected 11 videos due to mimium frame. The first eight 00:00:13 log (covers 104 seconds, leaving 14 seconds left). Thus second to last video (ninth) should have 20 frames (4 seconds) removed so will equal 00:00:09 seconds. And thus the final video (tenth) will be 00:00:05 seconds long.

### Testing with simplist in/out settings

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-frames-removed/ \
	--output_filepath tests/output/mode2/test4/UKHB001v205-frames-removed.mp4
```

Directory has 590 items. Expected 2 videos out. One 00:01:00 (300 frames max) and the second 00:00:58.

### Testing with adding nadir

```shell
python3 gopro2gsv.py \
	--input_directory tests/UKHB001v205-frames-removed/ \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--size_of_nadir 30 \
	--keep_extracted_frames \
	--output_filepath tests/output/mode2/test5/UKHB001v205-frames-removed
```

Directory has 590 items. Expected 2 videos out. One 00:01:00 (300 frames max) and the second 00:00:58. Both should have nadir.

=========

## Mode 3 (equirectangular mp4 video -> timelapse frames -> final video)

=========

### Extract frames from video input at 0.5 FPS and rebuild video with normal length (300 frames)

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--extract_fps 0.5 \
	--keep_extracted_frames \
	--output_filepath tests/output/mode3/test1/GS016843.mp4
```

ffmpeg extracts 95 frames = 95 / 5 = 19 seconds final output

Test some of the extracted frames to ensure geotagging is as expected (photos are 2 seconds apart and start from the first time in GPX file)

Check GPX

```xml
      <trkpt lat="44.9164189" lon="6.5483082">
        <ele>2324.285</ele>
        <time>2023-03-02T08:13:00.904000Z</time>
        <extensions>
          <gopro2gsv:InputPhoto>tests/output/mode3/test1/GS016843.mp4/_preprocessing/FRAME-00001.jpg</gopro2gsv:InputPhoto>
        </extensions>
      </trkpt>
```

```shell
exiftool tests/output/mode3/test1/GS016843-images/FRAME-00001.jpg -GPSDateTime
# GPS Date/Time                   : 2023:03:02 08:13:00.904Z
exiftool tests/output/mode3/test1/GS016843-images/FRAME-00002.jpg -GPSDateTime
# GPS Date/Time                   : 2023:03:02 08:13:02.884Z
exiftool tests/output/mode3/test1/GS016843-images/FRAME-00003.jpg -GPSDateTime
# GPS Date/Time                   : 2023:03:02 08:13:04.860952005Z
exiftool tests/output/mode3/test1/GS016843-images/FRAME-00004.jpg -GPSDateTime
# GPS Date/Time                   : 2023:03:02 08:13:06.899Z
```

### Extract frames from video input at 0.5 FPS and rebuild video with 20 second max (100 frames) -- simple split

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--extract_fps 2 \
	--max_output_video_secs 20 \
	--keep_extracted_frames \
	--output_filepath tests/output/mode3/test2/GS016843.mp4
```

ffmpeg extracts 376 frames = 376 / 5 = 75.2 seconds final output. 75.2/20 = 3.76. Thus expect 4 videos output. The first three 00:00:20 long. The fouth 00:00:14.800

### Extract frames from video input at 0.5 FPS and rebuild video with 37 second max (185 frames) -- complex split

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--extract_fps 2 \
	--max_output_video_secs 37 \
	--keep_extracted_frames \
	--output_filepath tests/output/mode3/test3/GS016843.mp4
```

ffmpeg extracts 376 frames = 376 / 5 = 75.2 seconds final output. 75.2/37 = 2.03. Expect 3 videos. The first video 00:00:37, the second video 00:00:35 seconds (as need to remove 20 frames/2 secs to satify minumum length of last video), and final video would be 00:00:03.200.

### Extract frames from video input at 0.5 FPS and add a nadir with 15 % height keep frames

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--extract_fps 2 \
	--keep_extracted_frames \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--size_of_nadir 15 \
	--output_filepath tests/output/mode3/test4/GS016843
```

ffmpeg extracts 376 frames = 376 / 5 = 75.2 seconds final output. Thus expect 2 videos output. One 00:01:00 long (max allowed length), and one 00:00:15.200. With a nadir.

### Extract frames from video input at 0.5 FPS do not keep frames

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--extract_fps 2 \
	--output_filepath tests/output/mode3/test5/GS016843
```


=========

## Mode 4 (.360 mode -> max2sphere -> timelapse frames -> final video (for MAX cameras))

=========


```shell
python3 gopro2gsv.py \
	--input_video tests/360_file/GS019359.360 \
	--extract_fps 0.5 \
	--keep_extracted_frames \
	--output_filepath tests/output/mode4/test1/GS019359.mp4
```


GS019359.360










