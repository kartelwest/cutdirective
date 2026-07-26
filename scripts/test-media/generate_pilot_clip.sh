#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="$(cd "$(dirname "$0")/../.." && pwd)/sample-data"
mkdir -p "$OUTPUT_DIR"

VIDEO="$OUTPUT_DIR/pilot_video.mp4"
AUDIO_WAV="$OUTPUT_DIR/pilot_audio.wav"
FINAL="$OUTPUT_DIR/pilot_clip.mp4"

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Generate 5s speech audio (16 kHz mono) with espeak-ng
espeak-ng -w "$AUDIO_WAV" -s 130 -p 50 "This is a test video for Cut Directive AI. Scene one. Scene two. Scene three. Done."
ffmpeg -y -i "$AUDIO_WAV" -ar 16000 -ac 1 "$OUTPUT_DIR/pilot_audio_16k.wav"

# Build a 5-second video with four different colored scenes and a text label
ffmpeg -y -f lavfi -i "color=c=red:s=1280x720:d=1.25" \
  -f lavfi -i "color=c=green:s=1280x720:d=1.25" \
  -f lavfi -i "color=c=blue:s=1280x720:d=1.25" \
  -f lavfi -i "color=c=yellow:s=1280x720:d=1.25" \
  -filter_complex "
    [0:v]drawtext=fontfile=$FONT:text='Scene 1':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[v0];
    [1:v]drawtext=fontfile=$FONT:text='Scene 2':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[v1];
    [2:v]drawtext=fontfile=$FONT:text='Scene 3':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[v2];
    [3:v]drawtext=fontfile=$FONT:text='Scene 4':fontsize=60:fontcolor=black:x=(w-text_w)/2:y=(h-text_h)/2[v3];
    [v0][v1][v2][v3]concat=n=4:v=1:a=0[outv]
  " -map "[outv]" -pix_fmt yuv420p -r 30 "$VIDEO"

# Combine video and audio
ffmpeg -y -i "$VIDEO" -i "$OUTPUT_DIR/pilot_audio_16k.wav" -c:v copy -c:a aac -b:a 192k -shortest "$FINAL"

echo "Pilot clip generated: $FINAL"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -show_entries format=duration -of csv=p=0 "$FINAL"
