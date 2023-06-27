# ai-translation

AI translation for English study based on SRS, K2, Whisper, FFmpeg, OBS, Fairseq, and GPT.

## Usage

The following is the usage of the AI translation.

* FFmpeg or OBS: Ingest audio stream.
* SRS: Convert audio stream to HLS.
* Whisper or K2: ASR to convert audio to text.
* Fairseq or GPT: Translate text to multiple languages.

## FFmpeg

Install FFmpeg:

```bash
brew install ffmpeg
```

### SRS

Download SRS:

```bash
cd ~/git
git clone https://github.com/ossrs/srs.git
cd ~/git/srs/trunk
./configure
make
```

Config SRS:

```nginx
# ai.translation.conf
listen              1935;
max_connections     1000;
srs_log_tank        console;
daemon              off;
http_api {
    enabled         on;
    listen          1985;
}
http_server {
    enabled         on;
    listen          8080;
    dir             ./objs/nginx/html;
}
vhost __defaultVhost__ {
    hls {
        enabled         on;
        hls_fragment 20;
        hls_ts_file [app]/[stream]-[02]-[15][04][05]-[seq].ts;
        hls_cleanup off;
    }
}
```

Start SRS:

```bash
./objs/srs -c ai.translation.conf
```

Publish live stream to SRS by FFmpeg:

```bash
ffmpeg -re -i ~/git/srs/trunk/doc/source.flv -c copy \
  -f flv rtmp://localhost/live/livestream
```

Or by OBS:

* Server: `rtmp://localhost/live`
* Stream Key: `livestream`

## Whisper

Install whisper:

```bash
cd ~/git
git clone -b translation https://github.com/ossrs/whisper.git
cd ~/git/whisper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt 
```

### K2

Install lfs:

```bash
brew install git-lfs
```

Download models:

```bash
cd ~/git
GIT_LFS_SKIP_SMUDGE=1 git clone \
  https://huggingface.co/csukuangfj/sherpa-ncnn-streaming-zipformer-en-2023-02-13
cd ~/git/sherpa-ncnn-streaming-zipformer-en-2023-02-13
git lfs pull --include "*.bin"
```

Build K2:

```bash
cd ~/git
git clone https://github.com/k2-fsa/sherpa-ncnn
mkdir ~/git/sherpa-ncnn/build
cd ~/git/sherpa-ncnn/build
cmake ..
make -j6
```

### Fairseq

Install fairseq:

```bash
cd ~/git
git clone -b translation https://github.com/ossrs/fairseq.git
cd ~/git/fairseq
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt 
```

### Script

Download script:

```bash
cd ~/git
git clone https://github.com/ossrs/ai-translation.git
cd ~/git/ai-translation
python -m venv venv
```

Link tools:

```bash
cd ~/git/ai-translation
rm -f k2 && ln -sf ~/git/sherpa-ncnn/build/bin k2
rm -f whisper && ln -sf ~/git/whisper whisper
rm -f fairseq && ln -sf ~/git/fairseq fairseq
rm -f live && ln -sf ~/git/srs/trunk/objs/nginx/html/live live
rm -f models && ln -sf ~/git/sherpa-ncnn-streaming-zipformer-en-2023-02-13 models
```

Install dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Translate:

```bash
export OPENAI_PROXY=x.y.z
export OPENAI_API_KEY=sk-xxxyyyzzz
python translate.py --stream livestream --output example
```

### Player

Link directory:

```bash
cd ~/git/translation/player
rm -f out && ln -sf ../out .
```

Run web server for player:

```bash
cd ~/git/translation/player
go run .
```

Open in browser:

[http://localhost:9000/simple.html?in=example](http://localhost:9000/simple.html?in=example)

