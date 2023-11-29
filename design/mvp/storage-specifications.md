### Logging

We should implement verbose logging for each run so that this can be used for debugging.

### Errors

All errors should be captured nicely showing clear error messages to users.

### Database

The local SQLite database is structured with two tables;

* `input`
	* `id`: UUID v4 for input
	* `timestamp`: time of import
	* `cli_mode`: selected via CLI
	* `cli_input_path`: selected via CLI (either directory to images, or video path)
	* `cli_extract_fps`: selected via CLI
	* `cli_keep_extracted_frames`: selected via CLI
	* `cli_path_to_nadir`: selected via CLI
	* `cli_size_of_nadir`: selected via CLI
	* `cli_outlier_speed_meters_sec`: selected via CLI
	* `cli_max_output_video_secs`: selected via CLI
	* `cli_output_filepath`: selected via CLI
	* `cli_upload_to_streetview`: selected via CLI
	* `output_directory`
	* `streetview_id`
	* `streetview_status`
	* `steetview_error`
* `video2video` (for mode 1)
	* `input_id`: input ID video linked to
	* `id`: UUID v4 for video
	* `length`: extracted via exiftool
	* `Width`: extracted via exiftool
	* `Height`: extracted via exiftool
* `frames2video` (for mode 2, 3, 4 -- note for modes 3 and 4 shows photos extracted and processed before video made)
	* `input_id`: input ID video linked to
	* `id`: UUID v4 for video
	* `Width`
	* `Height`
	* `ProjectionType`
	* `GPSLatitudeRef`
	* `GPSLatitude`
	* `GPSLongitudeRef`
	* `GPSLongitude`
	* `GPSAltitudeRef`
	* `GPSAltitude`
	* `GPSTimeStamp`
	* `GPSDateStamp`
	* `time_secs_to_previous`
	* `time_secs_to_next`
	* `distance_km_to_previous`
	* `distance_km_to_next`
	* `speed_kmh_to_previous`
	* `speed_kmh_to_next`
	* `error_reported`
* `gsvauth`
	* stores oauth key
	