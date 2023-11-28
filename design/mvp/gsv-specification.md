### Uploading to GSV

#### API endpoint info

The video can be uploaded using the GSV `photoSequence` endpoint where the `InputType` is `VIDEO`

https://developers.google.com/streetview/publish/reference/rest/v1/photoSequence/create

Note, the `rawGpsTimeline` does not need to be passed, as the video has this data embedded in it.

#### GSV setup

Note, to use the Street View video API methods, you will need to setup a new project in Google Cloud to access the Google API's.

##### 1. Create project and enable API

To do this, login to the [GCP Console](https://console.developers.google.com/).

The project name can be anything you want. It will only be visible to you in the GCP Console.

This app requires the following Google API's to work:

* [Street View Publish API](https://console.cloud.google.com/apis/library/streetviewpublish.googleapis.com)

##### 2. Create Oauth credentials

If this is your first time creating a project you might see the message:

> "To create an OAuth client ID, you must first set a product name on the consent screen."

Click the "Configure consent screen" button to do this.

The only field you need to fill in is "Application name". This name will be shown when you authenticate to allow the script to use your Google account to publish to Street View.

Once you have set the required consent information, select "API & Services" > "Credentials".

Now select "Create credentials" > "OAuth client ID"

Select Application type as "Desktop Application".

Enter a name for the credentials (e.g. `gopro2gsv`. This is helpful for tracking what these credentials are for.

If everything is successful, Google will generate a client ID and client secret. Make a note of these.

You can place your Google Oauth application information in the `.env` file once created.

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### Checking GSV state post upload

Each upload goes through various processing states: https://developers.google.com/streetview/publish/reference/rest/v1/photoSequence/create#ProcessingState

A `PROCESSED` response for `ProcessingState` indicates the video has been successfully published to StreetView. 

A `FAILED` response means something went wrong, and the information is captured in `ProcessingFailureReason`.

`PENDING` and `PROCESSING` state indicates the process is still ongoing. For uploads in this state, a user should be able to run an update request to update the DB with the latest remote changes, should there have been any progress.