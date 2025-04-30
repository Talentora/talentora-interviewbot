import logging
import os
import json
from datetime import datetime
from livekit import api
from dotenv import load_dotenv

logger = logging.getLogger("voice-agent")


load_dotenv(dotenv_path=".env")


async def setup_recording(room_name, participant=None):
    """
    Set up recording for a LiveKit room and store it in Supabase storage bucket
    with an organized directory structure: user_id/job_id/recording_file.
    
    Args:
        room_name: The name of the LiveKit room to record
        participant: The participant object containing metadata with applicant_id and job_id
        
    Returns:
        The egress ID if recording was started successfully, None otherwise
    """
    
    try:

         # check if is demo and skip if true 
        if participant and participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                is_demo = metadata.get("is_demo", False)
                if is_demo:
                    logger.info(f"Demo interview detected for room {room_name} - skipping recording")
                    return None
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
        return egress_id
        
    except Exception as e:
        logger.error(f"Failed to set up recording for room {room_name}: {str(e)}", exc_info=True)
        return None