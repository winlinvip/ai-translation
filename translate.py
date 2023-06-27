
import time
starttime = time.time()

import os, re, subprocess, openai, argparse, psutil

parser = argparse.ArgumentParser(description="Translation")
parser.add_argument("--stream", type=str, required=True, help="Input stream name, for example, in/livestream")
parser.add_argument("--output", type=str, required=True, help="Output stream name, for example, player/out/livestream")
parser.add_argument("--proxy", type=str, required=False, help="OpenAI API proxy, for example, x.y.z")
parser.add_argument("--key", type=str, required=False, help="OpenAI API key, for example, xxxyyyzzz")
parser.add_argument("--trans", type=str, default='fairseq', help="Translation tool: fairseq, gpt. Default: fairseq")
parser.add_argument("--transsrc", type=str, default='asr', help="Source text for translation: asr, en. Default: asr")
parser.add_argument("--source", type=str, default='eng_Latn', help="Source language. Default: eng_Latn")
parser.add_argument("--target", type=str, default='zho_Hans', help="Target language. Default: zho_Hans")

args = parser.parse_args()

INPUT=rf"{args.stream}-.*\.ts$"
OUTPUT=f"{args.output}"
# available models: 'tiny', 'base', 'small', 'medium', 'large'
# or english-only models: 'tiny.en', 'base.en', 'small.en', 'medium.en'
# See https://github.com/ossrs/whisper#available-models-and-languages
WHIPSER_MODEL="small"
# available models: 'facebook/nllb-200-distilled-600M', 'facebook/nllb-200-1.3B', 'facebook/nllb-200-distilled-1.3B', 'facebook/nllb-200-3.3B'
FAIRSEQ_MODEL="facebook/nllb-200-distilled-600M"

def mem_info():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    msg = mem_info.rss / (1024 * 1024)
    return f"memory={msg:.1f}MB"

def cost(starttime):
    return f"cost={(time.time() - starttime):.2f}s"

logs = []
logs.append(f"whisper-model={WHIPSER_MODEL}")
logs.append(f"translation={args.trans}")
if args.trans == 'fairseq':
    logs.append(f"fairseq-model={FAIRSEQ_MODEL}")
logs.append(f"trans-source={args.transsrc}")
logs.append(f"lang-source={args.source}")
logs.append(f"lang-target={args.target}")
logs.append(mem_info())
logs.append(cost(starttime))
print(f"args input={INPUT}, output={OUTPUT}, {', '.join(logs)}")

PROMPT_EN="Correct typo while maintain the original structure: "
PROMPT_EN_POSTFIX="Make sure to directly output the result without details."
PRMOPT_CN="Translate to Chinese: "

if args.trans == 'gpt':
    if args.key is not None:
        openai.api_key = args.key
    elif os.environ.get("OPENAI_API_KEY") is not None:
        openai.api_key = os.environ.get("OPENAI_API_KEY")
    else:
        raise Exception("OPENAI_API_KEY is not set")

    if args.proxy is not None:
        openai.api_base = "http://" + args.proxy + "/v1/"
    elif os.environ.get("OPENAI_PROXY") is not None:
        openai.api_base = "http://" + os.environ.get("OPENAI_PROXY") + "/v1/"
    else:
        print("Warning: OPENAI_PROXY is not set")

starttime = time.time()
print(f"whisper model {WHIPSER_MODEL} loading...")
import whisper
whisper_model = whisper.load_model(WHIPSER_MODEL)
print(f"whisper model loaded: {WHIPSER_MODEL}, {mem_info()}, {cost(starttime)}")

#huggingface/tokenizers: The current process just got forked, after parallelism has already been used. Disabling parallelism to avoid deadlocks...
#To disable this warning, you can either:
#	- Avoid using `tokenizers` before the fork if possible
#	- Explicitly set the environment variable TOKENIZERS_PARALLELISM=(true | false)
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
starttime = time.time()
print(f"fairseq model {FAIRSEQ_MODEL} loading...")
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
model = AutoModelForSeq2SeqLM.from_pretrained(FAIRSEQ_MODEL)
tokenizer = AutoTokenizer.from_pretrained(FAIRSEQ_MODEL)
en_translator = pipeline('translation', model=model, tokenizer=tokenizer, src_lang=args.source, tgt_lang=args.source)
cn_translator = pipeline('translation', model=model, tokenizer=tokenizer, src_lang=args.source, tgt_lang=args.target)
print(f"fairseq model loaded: {FAIRSEQ_MODEL}, {mem_info()}, {cost(starttime)}")

def translate(translator, text):
    result = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if paragraph == '':
            continue
        sentences = paragraph.split('.')
        for sentence in sentences:
            if sentence == '':
                continue
            output = translator(f"{sentence}.", max_length=128)
            translated_text = output[0]['translation_text']
            result.append(f"{translated_text} ")
        result.append('\n')
    return ''.join(result)

def get_sorted_ts_files(input_name, live_folder):
    ts_files = []
    ts_pattern = re.compile(input_name)

    for filename in os.listdir(live_folder):
        match = ts_pattern.match(filename)
        if match:
            ts_files.append(os.path.join(live_folder, filename))

    ts_files.sort()

    return ts_files

def execute_cli(cli):
    clis = cli.split(' ')
    print(' '.join(clis))
    result = subprocess.run(clis, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise Exception(f"command failed: {cli}, code is {result.returncode}")

def execute_result(cli):
    clis = cli.split(' ')
    print(' '.join(clis))
    result = subprocess.run(clis, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.stdout.decode('utf-8'), result.stderr.decode('utf-8')
    if result.returncode != 0:
        raise Exception(f"command failed: {cli}, code is {result.returncode}, {stdout}, {stderr}")
    return [stdout, stderr]

def get_asr_result(text):
    for line in text.split('\n'):
        if line.startswith('text: '):
            return line[6:]
    return None

def convert_ts_to_wav(in_filepath, out_filepath):
    if not os.path.exists(out_filepath):
        starttime = time.time()
        print(f"convert {in_filepath} to {out_filepath}")
        execute_cli(f"mkdir -p {os.path.dirname(out_filepath)}")
        execute_cli(f"ffmpeg -i {in_filepath} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y {out_filepath}")
        print(f"convert {in_filepath} to {out_filepath}, {mem_info()}, {cost(starttime)}")

def move_ts_to_output(in_filepath, out_tsfile):
    if not os.path.exists(out_tsfile):
        print(f"move {in_filepath} to {out_tsfile}")
        execute_cli(f"mkdir -p {os.path.dirname(out_tsfile)}")
        execute_cli(f"mv {in_filepath} {out_tsfile}")

def generate_asr(in_filepath, out_filepath, out_asr):
    if not os.path.exists(out_asr) and os.path.exists(out_filepath):
        starttime = time.time()
        print(f"generate ASR {out_filepath} to {out_asr}")
        execute_cli(f"mkdir -p {os.path.dirname(out_asr)}")
        result = whisper_model.transcribe(out_filepath, fp16=False)
        asr_text = result["text"]
        if asr_text is None:
            return
        if asr_text.strip() == '':
            raise CustomException(in_filepath, f"ASR text is empty, file is {out_filepath}")
        asr_text = asr_text.lower()
        print(f"Write ASR {out_asr}, text is {asr_text}, {mem_info()}, {cost(starttime)}")
        with open(out_asr, 'w') as f:
            f.write(asr_text)

# Translate ASR to Chinese.
def translate_to_cn(out_trans_cn, out_finalasr, previous_out_asr, previous_out_trans_cn):
    for i in range(3):
        try:
            if not os.path.exists(out_trans_cn) and os.path.exists(out_finalasr):
                starttime = time.time()
                with open(out_finalasr, 'r') as f:
                    src_text = f.read()
                if src_text.strip() == '<unk>':
                    print(f"Warning: ASR {out_finalasr} is <unk>, ignore")
                    return
                if args.trans == 'fairseq':
                    trans_text = translate(cn_translator, src_text)
                else:
                    messages = []
                    if previous_out_asr is not None and os.path.exists(previous_out_asr):
                        with open(previous_out_asr, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "user", "content": f"{PRMOPT_CN}\n'{previous_text}'"})
                    if previous_out_trans_cn is not None and os.path.exists(previous_out_trans_cn):
                        with open(previous_out_trans_cn, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "assistant", "content": f"{previous_text}"})
                    messages.append({"role": "user", "content": f"{PRMOPT_CN}\n'{src_text}'"})
                    completion = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                    )
                    trans_text = completion.choices[0].message.content
                print(f"Translate {src_text} to {trans_text}, {mem_info()}, {cost(starttime)}")
                with open(out_trans_cn, 'w') as f:
                    f.write(trans_text)
            break
        except Exception as e:
            print(f"Translate to Chinese failed: {e}")
            if i == 3:
                raise e

# Translate English to Chinese.
def translate_to_cn2(out_trans_cn, out_trans_en, previous_out_trans_en, previous_out_trans_cn):
    for i in range(3):
        try:
            if not os.path.exists(out_trans_cn) and os.path.exists(out_trans_en):
                starttime = time.time()
                with open(out_trans_en, 'r') as f:
                    src_text = f.read()
                if src_text.strip() == '':
                    print(f"Warning: English {out_trans_en} is empty, ignore")
                    return
                if args.trans == 'fairseq':
                    trans_text = translate(cn_translator, src_text)
                else:
                    messages = []
                    if previous_out_trans_en is not None and os.path.exists(previous_out_trans_en):
                        with open(previous_out_trans_en, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "user", "content": f"{PRMOPT_CN}\n'{previous_text}'"})
                    if previous_out_trans_cn is not None and os.path.exists(previous_out_trans_cn):
                        with open(previous_out_trans_cn, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "assistant", "content": f"{previous_text}"})
                    messages.append({"role": "user", "content": f"{PRMOPT_CN}\n'{src_text}'"})
                    completion = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                    )
                    trans_text = completion.choices[0].message.content
                print(f"Translate {src_text} to {trans_text}, {mem_info()}, {cost(starttime)}")
                with open(out_trans_cn, 'w') as f:
                    f.write(trans_text)
            break
        except Exception as e:
            print(f"Translate to Chinese failed: {e}")
            if i == 3:
                raise e

# Translate ASR to English.
def translate_to_en(out_trans_en, out_finalasr, previous_out_asr, previous_out_trans_en):
    for i in range(3):
        try:
            if not os.path.exists(out_trans_en) and os.path.exists(out_finalasr):
                starttime = time.time()
                with open(out_finalasr, 'r') as f:
                    src_text = f.read()
                if src_text.strip() == '<unk>':
                    print(f"Warning: ASR {out_finalasr} is <unk>, ignore")
                    return
                if args.trans == 'fairseq':
                    trans_text = translate(en_translator, src_text)
                else:
                    messages = []
                    if previous_out_asr is not None and os.path.exists(previous_out_asr):
                        with open(previous_out_asr, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "user", "content": f"{PROMPT_EN}\n'{previous_text}'"})
                    if previous_out_trans_en is not None and os.path.exists(previous_out_trans_en):
                        with open(previous_out_trans_en, 'r') as f:
                            previous_text = f.read()
                        messages.append({"role": "assistant", "content": f"{previous_text}"})
                    messages.append({"role": "user", "content": f"{PROMPT_EN}\n'{src_text}'\n{PROMPT_EN_POSTFIX}"})
                    completion = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                    )
                    trans_text = completion.choices[0].message.content
                print(f"Translate {src_text} to {trans_text}, {mem_info()}, {cost(starttime)}")
                with open(out_trans_en, 'w') as f:
                    f.write(trans_text)
            break
        except Exception as e:
            print(f"Rephrase to English failed: {e}")
            if i == 3:
                raise e

class CustomException(Exception):
    def __init__(self, filepath, message):
        self.filepath = filepath
        super().__init__(f"An error occurred with the file: {filepath}, {message}")

previous_in_filepath = None
previous_out_asr = None
previous_out_trans_cn = None
previous_out_trans_en = None
def loop(ignoreFiles):
    global previous_in_filepath, previous_out_asr, previous_out_trans_cn, previous_out_trans_en

    in_filepaths = get_sorted_ts_files(os.path.basename(INPUT), os.path.dirname(INPUT))
    if len(in_filepaths) > 0:
        print(f"Found {len(in_filepaths)} files in {INPUT} {in_filepaths}")
    print(f"Found {len(in_filepaths)} files in {INPUT}, and ignore {ignoreFiles}")

    for in_filepath in in_filepaths:
        out_asr = out_trans_cn = out_trans_en = None
        if in_filepath in ignoreFiles:
            continue
        try:
            starttime = time.time()
            in_basename = os.path.splitext(os.path.basename(in_filepath))[0]
            # Convert TS to WAV
            out_filepath = os.path.join(OUTPUT, f"{in_basename}.wav")
            convert_ts_to_wav(in_filepath, out_filepath)
            # Generate ASR
            out_asr = os.path.join(OUTPUT, f"{in_basename}.asr.txt")
            generate_asr(in_filepath, out_filepath, out_asr)
            # Rephrase the final text to English
            out_trans_en = os.path.join(OUTPUT, f"{in_basename}.trans.en.txt")
            translate_to_en(out_trans_en, out_asr, previous_out_asr, previous_out_trans_en)
            # Translate the final text to Chinese
            out_trans_cn = os.path.join(OUTPUT, f"{in_basename}.trans.cn.txt")
            if args.transsrc == 'asr':
                translate_to_cn(out_trans_cn, out_asr, previous_out_asr, previous_out_trans_cn)
            else:
                translate_to_cn2(out_trans_cn, out_trans_en, previous_out_trans_en, previous_out_trans_cn)
            # Move the input sourc file to OUTPUT.
            out_infile = os.path.join(OUTPUT, f"{in_basename}.ts")
            move_ts_to_output(in_filepath, out_infile)
            in_filepath = out_infile
            print(f"Finished {in_filepath} to {out_infile}, {mem_info()}, {cost(starttime)}")
        finally:
            previous_in_filepath = in_filepath
            previous_out_asr = out_asr
            previous_out_trans_cn = out_trans_cn
            previous_out_trans_en = out_trans_en

    return in_filepaths

exception_count = 0
ignoreFiles = []
while True:
    try:
        in_filepaths = None
        in_filepaths = loop(ignoreFiles)
        exception_count = 0
    except CustomException as e:
        print(f"CustomException: {e}")
        ignoreFiles.append(e.filepath)
    except Exception as e:
        print(f"Exception: {e}")
        exception_count += 1
        if exception_count > 3:
            raise e
        time.sleep(3)
    finally:
        if in_filepaths is None or len(in_filepaths) <= 0:
            time.sleep(3)
        else:
            time.sleep(0.3)
