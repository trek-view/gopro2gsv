# Test cases

Test cases for gopro2gsv

## Video mode (single mp4)

### No frame extraction, add a nadir

```shell
python3 gopro2gsv.py \
	--input_video tests/ski/GS016843.mp4 \
	--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
	--output_filepath tests/output/
```

### Frame at extraction

```shell
python3 gopro2gsv.py \
--upload_to_streetview \
--input_video tests/ski/GS016843.mp4 \
--path_to_nadir stock_nadirs/without_gopro/trek_view_full_nadir.png \
--output_filepath path/to/video-with-nadir.mp4
```


--extract_fps