#!/usr/bin/env python3

import argparse
import itertools
import json
import os
import shutil
import subprocess
import sys
import urllib.request

DESCRIPTION = """
This specialized tool can be used to replicate results from rmtg.co/benchmark by suitably
formatting and scoring output from the Mod9 ASR Engine.
It reads lines of JSON (i.e. JSONL format) from stdin and prints a report on stdout, saving
files in a work directory.
This uses the official NIST SCTK software, which is expected to be installed on the system,
and also requires certain reference data files which might be downloaded.
Each of those dependencies is installed in the mod9/asr Docker image for convenience.
The Switchboard audio data is needed for meaningful demonstration and could
be obtained from the Linguistic Data Consortium (https://catalog.ldc.upenn.edu/LDC2002S09).
"""

ALTERNATIVES_LEVELS = [
    'word',        # e.g. MBR-derived sausages
    'phrase',      # patent-pending Mod9 data structure
    'transcript',  # i.e. N-best
]

EXCLUDE_WORDS = [
    # These non-speech words are not transcribed in the reference, and will always hurt the score.
    '[cough]',
    '[laughter]',
    '[noise]',
    # These hesitations are optionally deletable in the reference, and can never help the score.
    'ah',
    'er',
    'huh',
    'mm',
    'uh',
    'um',
]

REFERENCE_GLM = 'switchboard-benchmark.glm'
REFERENCE_STM = 'switchboard-benchmark.stm'
REFERENCE_URL = 'https://mod9.io'

SCLITE_OPTS = '-F -D -o rsum pralign'

SCTK_TOOLS = [
    'csrfilt.sh',
    'rfilter1',
    'sclite',
]

SWITCHBOARD_SPEAKER_IDS = [
    "sw_4390_A",
    "sw_4390_B",
    "sw_4484_A",
    "sw_4484_B",
    "sw_4507_A",
    "sw_4507_B",
    "sw_4520_A",
    "sw_4520_B",
    "sw_4537_A",
    "sw_4537_B",
    "sw_4543_A",
    "sw_4543_B",
    "sw_4547_A",
    "sw_4547_B",
    "sw_4560_A",
    "sw_4560_B",
    "sw_4577_A",
    "sw_4577_B",
    "sw_4580_A",
    "sw_4580_B",
    "sw_4601_A",
    "sw_4601_B",
    "sw_4604_A",
    "sw_4604_B",
    "sw_4683_A",
    "sw_4683_B",
    "sw_4686_A",
    "sw_4686_B",
    "sw_4689_A",
    "sw_4689_B",
    "sw_4694_A",
    "sw_4694_B",
    "sw_4776_A",
    "sw_4776_B",
    "sw_4824_A",
    "sw_4824_B",
    "sw_4854_A",
    "sw_4854_B",
    "sw_4910_A",
    "sw_4910_B",
]

WORKDIR = '/tmp/switchboard-benchmark'


def error(message):
    print(f"ERROR: {message}")
    exit(1)


def run(command):
    try:
        return subprocess.run(command, capture_output=True, shell=True, check=True)
    except subprocess.SubprocessError:
        error(f"Unable to run '{command}'.")


def install_reference(reference_filename, reference_url):
    if os.path.exists(reference_filename):
        print(f"Found a previously installed reference file: {reference_filename}")
    else:
        print(f"Did not find {reference_filename}; downloading from {reference_url} ...")
        try:
            with urllib.request.urlopen(os.path.join(reference_url, reference_filename)) as resp:
                with open(reference_filename, 'wb') as glm_file:
                    shutil.copyfileobj(resp, glm_file)
        except Exception:
            error(f"Unable to download {reference_filename} from {reference_url}.")


def convert_jsonl_to_ctm(
        jsonl_filename, ctm_filename,
        key1, key2,
        alternatives=None,
        exclude_words=[],
        split_initialisms=True,
):
    """
    Convert ASR Engine output (JSON lines) to a NIST-formatted CTM file.

    The keys are used to lookup the corresponding reference in the STM file.
    The first key is traditionally the basename of a 2-channel audio file.
    The second key is traditionally a channel identifier, e.g. "A" or "B".

    If the alternatives argument is specified (as "phrase", "transcript", or
    "word"), the resulting file will make use of the CTM format's ability to
    represent alternative hypotheses. This somewhat lesser-known feature of
    the NIST SCTK software is unfortunately a bit buggy, though, and will
    require further post-processing to be handled correctly after filtering
    with the csrfilt.sh tool.

    The list of exclude_words is used as a simple filter to remove words in
    ASR output that is not well matched to the reference conventions. For
    example, it is never helpful to transcribe non-speech noises, since the
    reference does not include these and they will become insertion errors.

    The split_initialisms argument is used to match a convention in the
    reference transcription: for example, Y M C A should be 4 single-letter
    words rather than one single word such as y._m._c._a.
    """
    with open(jsonl_filename, 'r') as jsonl_file, open(ctm_filename, 'w') as ctm_file:
        def write_ctm(key1, key2, begin_time, duration, word, confidence=None):
            # Some ASR systems have a convention of writing initialisms as "a._b._c."
            # But the Switchboard reference treats this as separate words "a", "b", "c".
            if split_initialisms and '_' in word:
                words = word.split('_')
                duration /= len(words)
                for w in words:
                    if len(w) == 2 and w.endswith('.'):
                        w = w[0]
                    write_ctm(key1, key2, begin_time, duration, w, confidence)
                    begin_time += duration
            else:
                if word == '':
                    word = '@'  # Special NIST SCTK convention to indicate null word.
                ctm_file.write(f"{key1} {key2} {begin_time:0.3f} {duration:0.3f} {word}")
                if confidence:
                    ctm_file.write(f" {confidence}")
                ctm_file.write('\n')

        def write_words(key1, key2, begin_time, duration, words):
            duration /= len(words)
            for word in words:
                write_ctm(key1, key2, begin_time, duration, word)
                begin_time += duration

        for line in jsonl_file:
            reply = json.loads(line)
            if not reply.get('final'):
                # Skip replies that do no represent a finalized transcript result.
                continue
            if alternatives is None:
                if 'words' in reply:
                    for word_obj in reply['words']:
                        if 'interval' not in word_obj:
                            # TODO: we could try to infer these from the transcript-level interval.
                            error('Word-level intervals are expected.')
                        begin_time = word_obj['interval'][0]
                        duration = word_obj['interval'][1] - begin_time

                        word = word_obj['word']
                        if not word:
                            # This won't happen with Mod9 ASR Engine, but could in theory represent
                            # a situation in which the top-ranked word alternative is silence.
                            error('Unexpected empty word.')

                        if word in exclude_words:
                            continue

                        confidence = word_obj.get('confidence')

                        write_ctm(key1, key2, begin_time, duration, word, confidence)
                else:
                    # TODO: split reply.transcript with uniformly inferred word-level times.
                    # This may be helpful when processing output from systems that do not support
                    # word-level timestamps, such as human transcription or some E2E ASR systems.
                    error('Word-level intervals are expected.')

            else:
                if alternatives == 'phrase':
                    if 'phrases' not in reply:
                        error('Phrase-level alternatives are expected.')
                    for phrase_obj in reply['phrases']:
                        if 'interval' not in phrase_obj:
                            error('Phrase-level intervals are expected.')
                        begin_time = phrase_obj['interval'][0]
                        duration = phrase_obj['interval'][1] - begin_time

                        if 'alternatives' not in phrase_obj:
                            error('Phrase-level alternatives are expected.')
                        alts = phrase_obj['alternatives']

                        for alt in alts:
                            words = []
                            for w in alt['phrase'].split():
                                if w in exclude_words:
                                    w = '@'  # Special NIST SCTK convention for optional word.
                                words.append(w)
                            alt['phrase'] = ' '.join(words)
                            if alt['phrase'] == '':
                                alt['phrase'] = '@'

                        ctm_file.write(f"{key1} {key2} * * <ALT_BEGIN>\n")
                        for alt in alts[:-1]:
                            words = alt['phrase'].split()
                            write_words(key1, key2, begin_time, duration, words)
                            ctm_file.write(f"{key1} {key2} * * <ALT>\n")
                        words = alts[-1]['phrase'].split()
                        write_words(key1, key2, begin_time, duration, words)
                        ctm_file.write(f"{key1} {key2} * * <ALT_END>\n")
                elif alternatives == 'transcript':
                    if 'interval' not in reply:
                        error('Transcript-level intervals are expected.')
                    begin_time = reply['interval'][0]
                    duration = reply['interval'][1] - begin_time

                    if 'alternatives' not in reply:
                        error('Transcript-level alternatives are expected.')
                    alts = reply['alternatives']

                    for alt in alts:
                        words = []
                        for w in alt['transcript'].split():
                            if w in exclude_words:
                                w = '@'  # Special NIST SCTK convention for optional word.
                            words.append(w)
                        alt['transcript'] = ' '.join(words)
                        if alt['transcript'] == '':
                            alt['transcript'] = '@'

                    ctm_file.write(f"{key1} {key2} * * <ALT_BEGIN>\n")
                    for alt in alts[:-1]:
                        words = alt['transcript'].split()
                        write_words(key1, key2, begin_time, duration, words)
                        ctm_file.write(f"{key1} {key2} * * <ALT>\n")
                    words = alts[-1]['transcript'].split()
                    write_words(key1, key2, begin_time, duration, words)
                    ctm_file.write(f"{key1} {key2} * * <ALT_END>\n")
                elif alternatives == 'word':
                    if 'words' not in reply:
                        error('Word-level alternatives are expected.')
                    for word_obj in reply['words']:
                        if 'interval' not in word_obj:
                            error('Word-level intervals are expected.')
                        begin_time = word_obj['interval'][0]
                        duration = word_obj['interval'][1] - begin_time

                        if 'alternatives' not in word_obj:
                            error('Word-level alternatives are expected.')
                        alts = word_obj['alternatives']

                        for alt in alts:
                            if alt['word'] == '' or alt['word'] in exclude_words:
                                alt['word'] = '@'  # Special NIST SCTK convention for optional word.

                        # NOTE: in theory we should be able to use confidence for word alternatives.
                        # NIST BUG: cannot apply GLM to CTM with alternatives with confidence.
                        # TODO: report this to Jon Fiscus?
                        confidence = None

                        ctm_file.write(f"{key1} {key2} * * <ALT_BEGIN>\n")
                        for alt in alts[:-1]:
                            word = alt['word']
                            write_ctm(key1, key2, begin_time, duration, word, confidence)
                            ctm_file.write(f"{key1} {key2} * * <ALT>\n")
                        word = alts[-1]['word']
                        write_ctm(key1, key2, begin_time, duration, word, confidence)
                        ctm_file.write(f"{key1} {key2} * * <ALT_END>\n")
                else:
                    error('Unexpected alternatives level.')


def expand_alt_section(alt_section, max_expansions=None):
    """Helper function for refilter_ctm."""
    spans = [['']]
    alt_separator_line = ''
    for line in alt_section.strip().split('\n'):
        if '<ALT_BEGIN>' in line:
            spans.append([''])
        elif '<ALT_END>' in line:
            alt_separator_line = line.replace('<ALT_END>', '<ALT>').strip() + '\n'
            spans.append([''])
        elif '<ALT>' in line:
            spans[-1].append('')
        else:
            spans[-1][-1] += line + '\n'
    alts = list(itertools.product(*spans))
    if max_expansions and len(alts) > max_expansions:
        # TODO: figure out how to fix SCTK to handle this without a segfault.
        alts = alts[:max_expansions]
        print(f"WARNING: only expanding {len(alts)} nested alternatives due to SCTK bug.")
    expanded_alt_sections = [''.join(s) for s in alts]
    return alt_separator_line.join(expanded_alt_sections)


def refilter_ctm(ctm_in_filename, ctm_out_filename, max_expansions=None):
    """
    Post-process a CTM file that was produced by running the NIST SCTK tool
    csrfilt.sh on an original input CTM including hypothesis alternations.

    These become doubly-nested, e.g.:
    sw_4390 A * * <ALT_BEGIN>
    ...1...
    sw_4390 A * * <ALT_BEGIN>
    ...2...
    sw_4390 A * * <ALT>
    ...3...
    sw_4390 A * * <ALT_END>
    ...4...
    sw_4390 A * * <ALT_END>

    The solution is to expand these into singly-nested alternations, as
    the Cartesian product of the alternated sections, e.g.:
    sw_4390 A * * <ALT_BEGIN>
    ...1...
    ...2...
    ...4...
    sw_4390 A * * <ALT>
    ...1...
    ...3...
    ...4...
    sw_4390 A * * <ALT_END>

    Unfortunately, this can create rather long alternations, particularly
    for transcript-level N-best alternatives. This can cause problems for
    the downstream NIST SCTK sclite software which may segfault due to
    hardcoded buffer lengths. To mitigate this, set max_expansions. This
    shouldn't be needed for word-level or phrase-level alternatives.
    """
    in_alt = False
    in_nested_alt = False
    alt_sections = None
    alt_begin_line = None
    alt_end_line = None
    alt_separator_line = None

    with open(ctm_in_filename, 'r') as ctm_in_file, open(ctm_out_filename, 'w') as ctm_out_file:
        for line in ctm_in_file:
            if '<ALT_BEGIN>' in line:
                alt_begin_line = line
                if in_nested_alt:
                    error('Unexpected doubly-nested alternative.')
                elif in_alt:
                    in_nested_alt = True
                    alt_sections[-1] += line
                else:
                    in_alt = True
                    alt_sections = ['']
                continue
            elif '<ALT_END>' in line:
                alt_end_line = line
                alt_separator_line = alt_end_line.replace('<ALT_END>', '<ALT>').strip() + '\n'
                if in_nested_alt:
                    in_nested_alt = False
                    alt_sections[-1] += line
                elif in_alt:
                    in_alt = False
                    ctm_out_file.write(alt_begin_line)
                    alt_sections = [expand_alt_section(a, max_expansions) for a in alt_sections]
                    ctm_out_file.write(alt_separator_line.join(alt_sections))
                    ctm_out_file.write(alt_end_line)
                else:
                    error('Unexpected end of alternative.')
                continue
            elif '<ALT>' in line:
                if in_nested_alt:
                    alt_sections[-1] += line
                elif in_alt:
                    alt_sections.append('')
                continue

            if in_alt or in_nested_alt:
                alt_sections[-1] += line
            else:
                ctm_out_file.write(line)


def convert_stm_1seg(old_stm_filename, new_stm_filename):
    """
    Convert the STM into a single long segment, which can in some cases
    slightly improve the sclite alignment algorithm or minimize WER, e.g.
    in situations where a pair of insertion/deletion errors are across a
    segment boundary and could be consolidated as a single substitution.
    This also helps in situations where the reference segmentation is
    not used by the ASR system (i.e. a more fair evaluation than typical
    for academic research scenarios); slight differences in word-level
    timing may exist between the ASR system and the reference segments.
    """
    curr_key = None  # This function assumes the STM is speaker-specific.
    transcripts = []
    for line in open(old_stm_filename):
        if line.startswith(';;'):  # comment lines
            continue
        key1, key2, spkid, begin_time, end_time, labels, transcript = line.strip().split(None, 6)
        key = (key1, key2, spkid, labels)
        if curr_key and curr_key != key:
            # TODO: it's not that hard to generalize this to a multi-speaker STM file.
            error('Cannot collapse segmentation of a reference STM with multiple speakers.')
        else:
            curr_key = key
            transcripts.append(transcript)
    with open(new_stm_filename, 'w') as f:
        key1, key2, spkid, labels = curr_key
        f.write(f"{key1} {key2} {spkid} 0 999999999 {labels} {' '.join(transcripts)}\n")


def nist_report(switchboard_speaker_id, show_errors=False):
    """
    Read the .pra and .raw files produced by the NIST SCTK sclite tool.
    Produce a less verbose and somewhat more informative report.
    """
    if show_errors:
        errors = []
        print('\nSegments where reference and hypothesis are mis-aligned:')
        for line in open(f"{switchboard_speaker_id}.nist.pra"):
            if line.startswith('Scores:'):
                fields = line.strip().split()
                n_cor = int(fields[5])
                n_sub = int(fields[6])
                n_del = int(fields[7])
                n_ins = int(fields[8])
                n_err = n_sub + n_del + n_ins
                n_ref = n_err + n_cor
                wer = n_err / n_ref * 100
            elif line.startswith('REF:'):
                ref_line = line
            elif line.startswith('HYP:'):
                if n_err > 0:
                    errors.append((n_err, wer, ref_line, line))
        errors.sort(key=lambda x: x[0])  # or x[1] to sort by WER.
        for n_err, wer, ref_line, hyp_line in errors:
            print(ref_line, end='')
            print(hyp_line, end='')
        print()

    sum_line = run(f"grep Sum {switchboard_speaker_id}.nist.raw").stdout.decode()
    fields = sum_line.strip().split()
    n_ref = int(fields[4])
    n_cor = int(fields[6])
    n_sub = int(fields[7])
    n_del = int(fields[8])
    n_ins = int(fields[9])
    print(f"Sum (#C #S #D #I): {n_cor} {n_sub} {n_del} {n_ins}")

    # These are not standard metrics, but can be rather enlightening.
    precision = n_cor / (n_cor + n_sub + n_ins)
    recall = n_cor / (n_cor + n_sub + n_del)
    print(f"Precision/Recall:  {precision:0.3f} / {recall:0.3f}")

    # This is the standard ASR metric, which has a lot of drawbacks.
    wer = (n_sub + n_del + n_ins) / n_ref * 100
    print(f"Word Error Rate:   {wer:0.2f}%")


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'switchboard_speaker_id',
        metavar='SW_SPEAKER_ID',
        help='Switchboard speaker identifier, including channel, such as "sw_4390_A" for example.',
        choices=SWITCHBOARD_SPEAKER_IDS,
    )
    parser.add_argument(
        '--alternatives',
        metavar='LEVEL',
        help='Word-, phrase-, or transcript-level alternatives used for oracle scoring.',
        choices=ALTERNATIVES_LEVELS,
    )
    parser.add_argument(
        '--exclude-words',
        metavar='LIST',
        default=','.join(EXCLUDE_WORDS),
        help='Comma-separated list of words to exclude from the CTM.',
    )
    parser.add_argument(
        '--max-expansions',
        metavar='INT',
        type=int,
        help='Mitigate SCTK bug by limiting nested alternative expansions, e.g. transcript-level.',
    )
    parser.add_argument(
        '--reference-glm',
        metavar='FILE',
        help='Name of NIST-formatted Global Language Mapping file.',
        default=REFERENCE_GLM,
    )
    parser.add_argument(
        '--reference-stm',
        metavar='FILE',
        help='Name of NIST-formatted Segment Time Mark file.',
        default=REFERENCE_STM,
    )
    parser.add_argument(
        '--reference-url',
        metavar='URL',
        help='Whence missing reference files may be downloaded.',
        default=REFERENCE_URL,
    )
    parser.add_argument(
        '--show-errors',
        action='store_true',
        help='Compare segment-level mis-alignment.',
    )
    parser.add_argument(
        '--show-overall',
        action='store_true',
        help='Report aggregate scores over corpus.',
    )
    parser.add_argument(
        '--single-segment-stm',
        action='store_true',
        help='Convert reference to a long segment.',
    )
    parser.add_argument(
        '--workdir',
        metavar='DIRECTORY',
        help='Where files will be saved for caching or debugging.',
        default=WORKDIR,
    )
    args = parser.parse_args()

    # This tool will report on stdout, but these saved files might be helpful for debugging.
    os.makedirs(args.workdir, exist_ok=True)
    os.chdir(args.workdir)
    print(f"Results will be saved in the work directory: {args.workdir}")

    # Check installed dependencies.
    install_reference(args.reference_glm, args.reference_url)
    install_reference(args.reference_stm, args.reference_url)
    for sctk_tool in SCTK_TOOLS:
        if not shutil.which(sctk_tool):
            error(f"Could not find {sctk_tool}; ensure that NIST SCTK is installed.")

    # Parse the Switchboard speaker identifier, renamed as `spkid` for convenience.
    spkid = args.switchboard_speaker_id
    filename_id, channel_id = spkid.rsplit('_', 1)

    print(f"Read Engine replies (JSON lines) from stdin: {spkid}.jsonl", flush=True)
    with open(spkid+'.jsonl', 'w') as f:
        for line in sys.stdin:
            f.write(line)

    print(f"Convert to NIST-formatted hypothesis format: {spkid}.ctm")
    convert_jsonl_to_ctm(spkid+'.jsonl', spkid+'.ctm',
                         filename_id, channel_id,
                         alternatives=args.alternatives,
                         exclude_words=args.exclude_words.split(','))

    print(f"Apply global mappings to make filtered file: {spkid}.ctm.filt")
    run(f"csrfilt.sh -i ctm -t hyp -dh {args.reference_glm} < {spkid}.ctm > {spkid}.ctm.filt")

    print(f"Fix SCTK bug (nested alternative expansion): {spkid}.ctm.refilt")
    refilter_ctm(spkid+'.ctm.filt', spkid+'.ctm.refilt', args.max_expansions)

    print(f"Extract reference transcription for speaker: {spkid}.stm")
    run(f"grep '^{filename_id} {channel_id} {spkid}' < {args.reference_stm} > {spkid}.stm")

    print(f"Apply global mappings to make filtered file: {spkid}.stm.filt")
    run(f"csrfilt.sh -i stm -t ref -dh {args.reference_glm} < {spkid}.stm > {spkid}.stm.filt")

    # TODO: report this to Jon Fiscus?
    print(f"Fix SCTK bug (optional delete alternatives): {spkid}.stm.refilt")
    run('sed "s,(/),/,g; s,({,{(,g; s,}),)},g"' + f" < {spkid}.stm.filt > {spkid}.stm.refilt")

    stm = f"{spkid}.stm.refilt"
    if args.single_segment_stm:
        print(f"Convert the reference into one long segment: {spkid}.stm.refilt.1seg")
        convert_stm_1seg(stm, f"{spkid}.stm.refilt.1seg")
        stm = f"{spkid}.stm.refilt.1seg"

    print(f"Run the NIST SCLITE tool to produce reports: {spkid}.nist.*", flush=True)
    run(f"sclite -h {spkid}.ctm.refilt ctm -r {stm} stm -n {spkid}.nist {SCLITE_OPTS}")

    print(f"\nSpeaker {spkid}:")
    nist_report(spkid, args.show_errors)

    if args.show_overall:
        print('\nOverall corpus:')
        run("""cat *.nist.raw | grep Sum | awk '
{Snt+=$4;Wrd+=$5;Corr+=$7;Sub+=$8;Del+=$9;Ins+=$10} END \
{print" | Sum | "Snt"  "Wrd" | "Corr" "Sub" "Del" "Ins} \
' > overall.nist.raw""")
        nist_report('overall')


if __name__ == '__main__':
    main()
