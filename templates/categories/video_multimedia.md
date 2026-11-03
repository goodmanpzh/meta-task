### Category: Video and Multimedia Processing

Tasks involving video analysis, audio processing, multimedia format manipulation, and computer vision on video/image streams.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Extract specific information from video frames (OCR, object detection, event detection)
- Analyze video to detect events or transitions (sports analysis, scene changes)
- Process audio tracks (transcription, beat detection, noise removal)
- Convert between multimedia formats with specific requirements
- Implement video codecs or understand encoding internals
- Extract subtitles or overlay text from videos
- Synchronize audio and video streams
- Detect and track objects across video frames
- Generate video from frames or animations
- Analyze game recordings to extract moves/actions (Zork commands, chess moves)
- Implement graphics renderers (ray tracing, path tracing)
- Build image processing pipelines (filters, transformations)

**Skills & Tools** (tag suggestions for your task):
- Core: `video-processing`, `multimedia`, `computer-vision`, `graphics`
- Tools: `ffmpeg`, `opencv`, `imagemagick`, `sox`, `mediainfo`
- Formats: `mp4`, `avi`, `mkv`, `wav`, `mp3`, `webm`, `png`, `ppm`
- Concepts: `frame-extraction`, `transcription`, `encoding`, `ray-tracing`
- Libraries: `moviepy`, `pydub`, `cv2`, `PIL`

**Possible Input Data** (be creative with environment files!):
- Video files (MP4, AVI, WebM) for analysis
- Audio files (WAV, MP3) for processing
- Frame sequences (PNG, JPEG folders)
- Subtitle files (SRT, VTT) for synchronization
- Reference transcriptions for accuracy testing
- Ground truth annotations for detection tasks
- Game recordings with known move sequences
- Scene description files for rendering
- 3D model files (OBJ, STL) for graphics tasks
- Reference images for comparison (SSIM, PSNR)

**Verification Approaches**:
- Extracted data matches expected values (timestamps, text, objects)
- Output format is valid and playable
- Transcription accuracy above threshold
- Correct frame/timestamp detection
- Audio/video sync within tolerance
- Image similarity metrics (SSIM, PSNR, MSE)
- File size/quality constraints met
- Detection accuracy metrics (precision, recall)

**Remember**: Video/multimedia tasks often involve large files and processing time. Design tasks with appropriately sized inputs and clear success criteria. Consider edge cases like variable frame rates, corrupted files, or unusual codecs!
