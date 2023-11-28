### Logging

We should implement verbose logging for each run so that this can be used for debugging.

### Errors

All errors should be captured nicely showing clear error messages to users.

### Database

The local SQLite database is structured with two tables;

* Video
	* User settings
	* Local path to output/logs
	* StreetView info
* Timelapse Images
	* User settings
	* Local path to output
	* StreetView info
* Photos (for photo input)
	* Contains photo data for timelapse image input
	* Key to Timelapse images/logs