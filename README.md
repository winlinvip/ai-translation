# ai-translation

[![](https://badgen.net/discord/members/yZ4BnPmHAd)](https://discord.gg/yZ4BnPmHAd)

AI translation for English study based on FFmpeg, Whisper, Fairseq, OBS, SRS, and GPT.

![](https://github.com/ossrs/ai-translation/assets/2777660/fc0bee11-1681-46ce-a249-d31e438525e7)

> Note: Additionally, it is capable of translating from one language to another without any limitations.

## Usage

The following is the usage of the AI translation.

### FFmpeg

You can install FFmpeg by following the instructions provided in the 
[FFmpeg documentation](https://ffmpeg.org/download.html).

For macOS to install FFmpeg:

```bash
brew install ffmpeg
```

Or Ubuntu to install FFmpeg:

```bash
apt-get install -y ffmpeg
```

Then, use FFmpeg to convert audio file to HLS:

```bash
mkdir -p ~/git/srs/trunk/objs/nginx/html/live
cd ~/git/srs/trunk/objs/nginx/html/live
ffmpeg -i ~/git/srs/trunk/doc/source.flv -c copy \
  -f hls -hls_time 15 -hls_segment_filename 'livestream-%04d.ts' \
  -y livestream.m3u8
```

Please examine the directory, as it should contain some HLS files:

```bash
ls -lh ~/git/srs/trunk/objs/nginx/html/live
#-rw-r--r--  632K Jun 28 07:36 livestream-0000.ts
#-rw-r--r--  194K Jun 28 07:36 livestream-0001.ts
#-rw-r--r--  303K Jun 28 07:36 livestream-0002.ts
```

Please note that the duration of each segment should be approximately 10~30 seconds, and 
the filenames of the segments should be arranged in alphabetical order.

### Translator

Download the main script and setup it by:

```bash
cd ~/git
git clone https://github.com/ossrs/ai-translation.git
cd ~/git/ai-translation
python3 -m venv venv
```

Next, create a python venv and install dependencies:

```bash
cd ~/git/ai-translation
source venv/bin/activate
pip install -r requirements.txt
```

Now, you can translate the HLS by:

```bash
python translate.py --output player/out/livestream \
  --stream ~/git/srs/trunk/objs/nginx/html/live/livestream
```

The tool will process files from `~/git/srs/trunk/objs/nginx/html/live/livestream-*.ts` 
and generate output in `player/out/livestream/*.txt`. Please examine the directory, as 
it should contain some HLS and translation text files:

```bash
ls -lh player/out/livestream
#-rw-r--r--   61B Jun 28 07:41 livestream-0000.asr.txt
#-rw-r--r--   42B Jun 28 07:41 livestream-0000.trans.cn.txt
#-rw-r--r--   46B Jun 28 07:41 livestream-0000.trans.en.txt
#-rw-r--r--  632K Jun 28 07:36 livestream-0000.ts
#-rw-r--r--  461K Jun 28 07:41 livestream-0000.wav
```

You can then view the translated results using a player, as described in the following 
chapter.

### Player

We have developed a player to play the HLS stream and link the segments with their 
corresponding translated text.

Please ensure that the translation output files are generated in the `player/out` 
directory. 

Then, run web server for player:

```bash
cd ~/git/translation/player
go run .
```

Open in browser:

[http://localhost:9000/simple.html?in=livestream](http://localhost:9000/simple.html?in=livestream)

Click the segment to play the HLS stream and view the translated text.

### (Optional) SRS

If you wish to receive streams from OBS or other encoding software, SRS can be 
utilized to transform the stream into HLS format.

First, download SRS and build it:

```bash
cd ~/git
git clone https://github.com/ossrs/srs.git
cd ~/git/srs/trunk
./configure
make
```

Next, create a file named `ai.translation.conf` and configure SRS with HLS to ensure 
that the segment names are arranged alphabetically:

```nginx
listen 1935;
max_connections 1000;
srs_log_tank console;
daemon off;
http_api {
    enabled on;
    listen 1985;
}
http_server {
    enabled on;
    listen 8080;
    dir ./objs/nginx/html;
}
vhost __defaultVhost__ {
    hls {
        enabled on;
        hls_fragment 15;
        hls_ts_file [app]/[stream]-[02]-[15][04][05]-[seq].ts;
        hls_cleanup off;
    }
}
```

Start SRS to accept streams:

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

## (Optional) Use GPT for Translate

If you prefer not to use Fairseq and instead want to use GPT for translation, you should 
configure the environment and execute the following command.

```bash
export OPENAI_PROXY=x.y.z
export OPENAI_API_KEY=sk-xxxyyyzzz
python translate.py --output player/out/livestream \
  --stream ~/git/srs/trunk/objs/nginx/html/live/livestream \
  --trans gpt
```

* `env OPENAI_PROXY` is for proxy, required if you are in China.
* `env OPENAI_API_KEY` is for GPT API key, required if you want to use GPT.
* `--trans gpt` is option to enable OpenAI GPT to translate.

After conducting some tests, I believe that Fairseq is quite comparable to GPT in terms of 
performance. However, GPT appears to generate slightly more natural output than Fairseq. 
Both options are sufficiently effective.

Since Fairseq is a free and open-source option, whereas GPT is a paid service, we have chosen 
to use Fairseq by default.

## (Optional) Annex A: About Whisper and Fairseq

We use the following tools to translate the audio stream:

* FFmpeg, OBS, or SRS: Ingest and convert audio stream to HLS.
* Whisper: ASR to convert audio to text.
* Fairseq or GPT: Translate text to multiple languages.

OBS, SRS, and GPT are not mandatory; you can simply utilize FFmpeg, Whisper, and Fairseq.

[Whisper](https://github.com/ossrs/whisper) is an ASR tool derived from the OpenAI 
Whisper open-source project, with an added tool.py to simplify its usage.

[Fairseq](https://github.com/ossrs/fairseq) is a translation tool derived from the meta 
fairseq open-source project, with an added tool.py to simplify its usage.

## (Optional) Annex B: Other Languages

It is capable of translating from one language to another without any limitations.

For example, translate from English to German:

```bash
python translate.py --output player/out/livestream \
  --stream ~/git/srs/trunk/objs/nginx/html/live/livestream \
  --source eng_Latn --target deu_Latn
```

* `--source eng_Latn` is the source language to input as English.
* `--target deu_Latn` is the target language to translate as German.

The following languages are some examples:

* eng_Latn: English written in Latin script
* zho_Hans: Chinese written in Simplified Han script
* kor_Hang: Korean written in Hangul script
* fra_Latn: French written in Latin script
* spa_Latn: Spanish written in Latin script
* ita_Latn: Italian written in Latin script
* deu_Latn: German written in Latin script
* jpn_Jpan: Japanese written in Japanese script, which includes Kanji, Hiragana, and Katakana
* pol_Latn: Polish written in Latin script

Other languages should also be supported, but we have not tested them, please see
[Whipser: Available models and languages](https://github.com/openai/whisper#available-models-and-languages)
and [Fairseq: No Language Left Behind](https://github.com/facebookresearch/fairseq/tree/nllb#no-language-left-behind) 
for detail.

Winlin, 2023
