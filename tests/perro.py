import instaloader
import tempfile
from pathlib import Path

# Get instance
L = instaloader.Instaloader(
    download_video_thumbnails=False,
    save_metadata=False,
    download_comments=False,
    download_geotags=False,
)

# Optionally, login or load session
# L.login(USER, PASSWORD)        # (login)
# L.interactive_login(USER)      # (ask password on terminal)
# L.load_session_from_file(USER) # (load session created w/
#                                #  `instaloader -l USERNAME`)
post = instaloader.Post.from_shortcode(L.context, "DHwU2jTCQ1N")



with tempfile.TemporaryDirectory() as temp_dir:
    # Create a temporary directory
    temp_path = Path(temp_dir)
    # Set the target directory to the temporary directory
    success = L.download_post(post, target=temp_path)

    # Check if the post was downloaded successfully
    assert success, "Post was not downloaded successfully"

    

