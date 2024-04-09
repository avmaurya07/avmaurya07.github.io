# Import necessary modules and packages
from flask import Flask, render_template, send_from_directory
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
from wtforms.validators import InputRequired
from deepgram import Deepgram
import json
import pysrt
from config import DEEPGRAM_API_KEY  # Import DEEPGRAM_API_KEY from a config file
file_response = ''

# Initialize Flask app
app = Flask(__name__)

# Configure Flask app
app.config['SECRET_KEY'] = 'supersecretkey'  # Set secret key for CSRF protection
app.config['UPLOAD_FOLDER'] = 'static/files'  # Define upload folder for uploaded files

# Define form class for file upload
class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])  # FileField for file upload
    submit = SubmitField("Upload File")  # SubmitField for form submission

# Define function to convert time to seconds
def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000

# Define function to create subtitle clips
def create_subtitle_clips(subtitles, videosize, fontsize=24, font='Arial', color='yellow', debug=False):
    subtitle_clips = []
    
    # Generate subtitle clips
    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time
        video_width, video_height = videosize
        # Create TextClip for subtitle
        text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, bg_color='black', size=(video_width*3/4, None), method='caption').set_start(start_time).set_duration(duration)
        subtitle_x_position = 'center'
        subtitle_y_position = video_height * 4 / 5 
        text_position = (subtitle_x_position, subtitle_y_position)                    
        subtitle_clips.append(text_clip.set_position(text_position))
    return subtitle_clips

# Define function to process uploaded file
def processFile(filePath):
    # Replace with your file path and audio mimetype
    PATH_TO_FILE = filePath
    MIMETYPE = 'audio/wav'
    global file_response

    # Initialize Deepgram SDK and get transcription
    def init_deepgram():
        global file_response
        dg_client = Deepgram(DEEPGRAM_API_KEY)  # Initialize Deepgram client with API key
        with open(PATH_TO_FILE, 'rb') as audio:
            source = {'buffer': audio, 'mimetype': MIMETYPE}
            options = {"punctuate": True, "model": "nova", "language": "en-US"}
            file_response = dg_client.transcription.sync_prerecorded(source, options)
            print('json response:')
            print(json.dumps(file_response, indent=4))
    
    # Call init_deepgram function
    init_deepgram()
    subtitle_data = file_response['results']['channels'][0]['alternatives'][0]['words']
    print(subtitle_data)
    
    # Extract the filename from the URL
    filename = os.path.basename(filePath)
    name, extension = os.path.splitext(filename)
    op_file = name + ".srt"
    print('output filename')
    print(op_file)

    # Function to convert data to SRT format
    def convert_to_srt(data, op_file):
        def format_time(seconds):
            # Convert seconds to hours, minutes, seconds, milliseconds format
            hours, remainder = divmod(seconds, 3600)
            minutes, remainder = divmod(remainder, 60)
            seconds, milliseconds = divmod(remainder, 1)
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds*1000):03d}"

        with open(op_file, 'w') as f:
            for i, entry in enumerate(data, start=1):
                start_time = format_time(entry['start'])
                end_time = format_time(entry['end'])
                subtitle_text = entry['punctuated_word']
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{subtitle_text}\n\n")
    
    # Write subtitle file
    convert_to_srt(subtitle_data, op_file)
    mp4filename = filePath
    srtfilename = op_file
    
    # Load video and SRT file
    video = VideoFileClip(mp4filename)
    subtitles = pysrt.open(srtfilename)
    output_video_file = 'static/files/output.mp4'
    print("Output file name: ", output_video_file)

    # Create subtitle clips
    subtitle_clips = create_subtitle_clips(subtitles, video.size)

    # Add subtitles to the video
    final_video = CompositeVideoClip([video] + subtitle_clips)

    # Write output video file
    final_video.write_videofile(output_video_file)

# Define route for home page
@app.route('/', methods=['GET','POST'])
@app.route('/home', methods=['GET','POST'])
def home():
    form = UploadFileForm()  # Create instance of UploadFileForm
    if form.validate_on_submit():
        # Obtain the file
        file = form.file.data
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))  # Save the uploaded file
        processFile(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))  # Process the uploaded file
        return render_template('play_video.html')  # Render template for playing the video
    return render_template('video_subtitle_generation_index.html', form=form)  # Render template for uploading file

# Define route for downloading output file
@app.route('/download')
def download_file():
    filename = 'output.mp4'
    return send_from_directory(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), filename, as_attachment=True)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
