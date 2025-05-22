import logging
import os
import json
from datetime import datetime
from livekit import api
from dotenv import load_dotenv
import boto3

logger = logging.getLogger("voice-agent")


load_dotenv(dotenv_path=".env")


# Custom JSON encoder to handle non-serializable objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


async def setup_recording(room_name, participant=None):
    """
    Set up recording for a LiveKit room and store it in Supabase storage bucket
    with an organized directory structure: user_id/job_id/recording_file.
    
    Args:
        room_name: The name of the LiveKit room to record
        participant: The participant object containing metadata with applicant_id and job_id
        
    Returns:
        Tuple containing (egress_id, user_id, job_id) if successful, (None, None, None) otherwise
    """
    
    try:

         # check if is demo and skip if true 
        if participant and participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                is_demo = metadata.get("is_demo", False)
                if is_demo:
                    logger.info(f"Demo interview detected for room {room_name} - skipping recording")
                    return None, None, None
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse participant metadata as JSON")

        # Default file path (in case we can't extract user_id/job_id)
        filepath = f"recordings/interview_{room_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        # Extract user_id (applicant_id) and job_id from participant metadata if available
        user_id = None
        job_id = None
        
        if participant and participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                user_id = metadata.get("applicant_id")
                job_id = metadata.get("job_id")
                
                if user_id and job_id:
                    logger.info(f"Using organized directory structure: {user_id}/{job_id}/")
                    # Create the organized filepath
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"interview_recording.mp4"
                    filepath = f"{user_id}/{job_id}/{filename}"
                else:
                    logger.warning("applicant_id or job_id not found in participant metadata, using default path")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse participant metadata as JSON, using default path")
        else:
            logger.info("No participant metadata available, using default path")
        

        # supabase_url = os.environ.get("SUPABASE_URL")
        bucket_name = os.environ.get("AWS_BUCKET_NAME")
        access_key = os.environ.get("AWS_ACCESS_KEY")
        secret_key = os.environ.get("AWS_SECRET_KEY")

        logger.info(f"BucketName: {bucket_name}")
        logger.info(f"AccessKey: {access_key}")
        logger.info(f"SecretKey: {secret_key}")
        # Create the recording request
        req = api.RoomCompositeEgressRequest(
            room_name=room_name,
            audio_only=False,
            file_outputs=[api.EncodedFileOutput(
                file_type=api.EncodedFileType.MP4,
                filepath=filepath,
                # Supabase storage integration
                s3=api.S3Upload(
                    bucket=bucket_name,
                    region="us-east-2",  
                    access_key=access_key,  
                    secret=secret_key, 
                    force_path_style=True,
                ),
            )],
        )

        # Initialize the LiveKit API client
        lkapi = api.LiveKitAPI()
        # Start the recording
        res = await lkapi.egress.start_room_composite_egress(req)
        # Close the API client
        await lkapi.aclose()
        
        egress_id = res.egress_id
        logger.info(f"Recording started successfully for room {room_name}, egress ID: {egress_id}, path: {filepath}")
        return egress_id, user_id, job_id
        
    except Exception as e:
        logger.error(f"Failed to set up recording for room {room_name}: {str(e)}", exc_info=True)
        return None, None, None


def save_transcript(conversation_transcripts, room_name, user_id=None, job_id=None):
    """
    Save conversation transcripts to the same S3 bucket as the recording.
    
    Args:
        conversation_transcripts: List of transcript segments with speaker and text
        room_name: The name of the LiveKit room
        user_id: The user ID (applicant_id) for organized directory structure
        job_id: The job ID for organized directory structure
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        logger.info(f"Saving transcript for room {room_name}")
        
        # Skip if no transcripts
        if not conversation_transcripts:
            logger.warning("No transcript data to save")
            return False
            
        # Determine filepath
        if user_id and job_id:
            transcript_filepath = f"{user_id}/{job_id}/interview_transcript.json"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            transcript_filepath = f"recordings/{user_id}/{job_id}/transcript_{timestamp}.json"
        
        # Format the transcript data
        transcript_data = {
            "room_name": room_name,
            "timestamp": datetime.now().isoformat(),
            "conversation": []
        }
        
        # Build the conversation as a simple array with speaker names
        for segment in conversation_transcripts:
            speaker = segment["speaker"]
            text = segment["text"]
            entry = {speaker: text}
            transcript_data["conversation"].append(entry)
        
        # Get S3 credentials
        bucket_name = os.environ.get("AWS_BUCKET_NAME")
        access_key = os.environ.get("AWS_ACCESS_KEY")
        secret_key = os.environ.get("AWS_SECRET_KEY")
        
        if not all([bucket_name, access_key, secret_key]):
            logger.error("Missing S3 credentials for transcript upload")
            return False
        
        # Upload transcript to S3 using boto3
        try:
            s3_client = boto3.client('s3',
                region_name="us-east-2",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=transcript_filepath,
                Body=json.dumps(transcript_data, indent=2, cls=CustomJSONEncoder),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded transcript to {transcript_filepath}")
            return True
        except Exception as s3_error:
            logger.error(f"S3 upload error: {str(s3_error)}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Failed to save transcript for room {room_name}: {str(e)}", exc_info=True)
        return False