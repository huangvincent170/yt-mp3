import sys
import subprocess
import re
import os
import shutil
import json
import argparse


'''
Parses a youtube url, returning its id
'''
def parse_url(url: str):
    url_result_groups = re.search(r'^.*(?:youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=)([^#\&\?]*).*$', url).groups()
    if not url_result_groups or len(url_result_groups) > 1:
        raise ValueError(f"Error parsing URL {url}")
    return url_result_groups[0]


'''
Returns a youtube url from a video id
'''
def url(id: str):
    return f'https://www.youtube.com/watch?v={id}'


'''
Downloads the audio, video, thumbnail, metadata json, and description of a video.
Args:
    video_id: The id of the video to download content for.
'''
def download_content(video_id: str):
    yt_dlp_command = ['yt-dlp',
        '-x',                               # extract audio
        '-k',                               # keep video
        '-o', '%(id)s.%(ext)s',             # set audio path to [youtube id].[extension]
        '--write-thumbnail',                # get thumbnail
        '--convert-thumbnails', 'png',      # convert thumbnail to png
        '--write-description',              # get description
        '--audio-format', 'mp3',            # convert audio to mp3
        '--audio-quality', '0',             # highest quality audio
        '--write-info-json',                # get metadata json
        f'{url(video_id)}',                 # youtube video url
    ]
    subprocess.run(yt_dlp_command, check=True)


'''
Checks if a youtube is autogenerated
'''
def is_autogenerated_video(description_path: str):
    description_str = None
    with open(description_path, mode='r') as description_file:
        description_str = description_file.read()

    if description_str and re.match(r'^[\S\s]*Auto-generated by YouTube\.$', description_str):
        return True
    return False


'''
Gets a frame of a video as an image
todo: select any frame instead of just first
'''
def get_frame(video_path: str, frame_path: str):
    ffmpeg_get_frame_command = ['ffmpeg',
        '-i', video_path,
        '-vf', 'select=eq(n\,5)',
        '-vframes', '1',
        f'{frame_path}'
    ]
    subprocess.run(ffmpeg_get_frame_command, check=True)


"""
Reads a video metadata info json file and sets the tag of an audio file
based on the first key it encounters in the json
"""
def set_metadata(metadata, audio_path, tag, *keys):
    value = None
    for key in keys:
        if key in metadata:
            value = metadata[key]
            break
    if value:
        subprocess.run(['eyeD3', f'--{tag}', f"{value}", f'{audio_path}'], check=True)


def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('-c', '--cover-art', metavar='cover-url', help='Sets the cover art to the first frame of the video')
    parser.add_argument('-k', '--keep', help='Keep temporary files', action='store_true')
    args = parser.parse_args()

    video_id = parse_url(args.url)
    print(video_id)


    # create and move into temporary directory
    tempdir_path = f'./{video_id}'
    os.mkdir(tempdir_path)
    os.chdir(tempdir_path)


    # download audio
    audio_path = f'./{video_id}.mp3'
    download_content(video_id)


    # get cover art
    cover_art_path = None
    is_autogenerated = is_autogenerated_video(f'{video_id}.description')
    print(f"is autogenerated: {is_autogenerated}")
    if args.cover_art:
        # get cover art from other video frame
        cover_art_id = parse_url(args.cover_art)
        download_content(cover_art_id)
        cover_art_path = f'./frame_{cover_art_id}.png'
        get_frame(f'./{cover_art_id}.webm', cover_art_path)
    elif is_autogenerated:
        # get cover art from current video frame
        cover_art_path = f'./frame_{video_id}.png'
        get_frame(f'./{video_id}.webm', cover_art_path)
    else:
        # use thumbnail as cover art
        cover_art_path = f'./{video_id}.png'


    # set cover art metadata 
    eyed3_cover_art_command = ['eyeD3',
        '--add-image', f'{cover_art_path}:FRONT_COVER',
        f'{audio_path}'
    ]
    subprocess.run(eyed3_cover_art_command, check=True)


    # set other metadata
    with open(f'{video_id}.info.json') as metadata_json_file:
        metadata = json.load(metadata_json_file)
        set_metadata(metadata, audio_path, 'artist', 'artist', 'channel')
        set_metadata(metadata, audio_path, 'title', 'track', 'title')
        set_metadata(metadata, audio_path, 'album', 'album', 'track', 'title')


    # clean up temp files
    os.chdir("../")
    shutil.copyfile(f'{tempdir_path}/{video_id}.mp3', f'./{video_id}.mp3')
    if not args.keep:
        shutil.rmtree(tempdir_path)

if __name__ == '__main__':
    main()
