![HEAR2021](https://neuralaudio.ai/assets/img/hear-header-sponsor.jpg)
# hear-preprocess

Dataset preprocessing code for the HEAR 2021 NeurIPS competition.

Unless you are a HEAR organizer or want to contribute a task,
you won't need this repo. Use
[hear-eval-kit](https://github.com/neuralaudio/hear-eval-kit/) to
evaluate your embedding models on these tasks.

This preprocessing is slow and disk-intensive but safe and careful.

## Cloud Usage

See [hear-eval's
README.spotty](https://github.com/neuralaudio/hear-eval-kit/blob/main/README.spotty.md)
for information on how to use spotty.

## Installation

```
pip3 install hearpreprocess
```

Tested with Python 3.7 and 3.8. Python 3.9 is not officially supported
because pip3 installs are very finicky, but it might work.

## Development

Clone repo:
```
git clone https://github.com/neuralaudio/hear-preprocess
cd hear-preprocess
```
Add secret task submodule:
```
git submodule init
git submodule update --remote
```
**_NOTE_**: Secret tasks are not available to participants. You
should skip the above step.

Install in development mode:
```
pip3 install -e ".[dev]"
```

Make sure you have pre-commit hooks installed:
```
pre-commit install
```

Running tests:
```
python3 -m pytest
```

### Preprocessing

You probably don't need to do this unless you are implementing the
HEAR challenge.

If you want to run preprocessing yourself:
* You will need `ffmpeg>=4.2` installed (possibly from conda-forge).
* You will need `soxr` support, which might require package
libsox-fmt-ffmpeg or [installing from
source](https://github.com/neuralaudio/hear-eval-kit/issues/156#issuecomment-893151305).

When using 'mode --default', this will take about several hours for
the open tasks.  150 GB free disk space is required while processing.
Final output is 11 GB.

mode --all (speech_commands full and nsynth 50h), on n1-standard-8,
16.5 hours.  560GB working disk, including final output.  Final
output 138GB.

These Luigi pipelines are used to preprocess the evaluation tasks
into a common format for downstream evaluation.

To run the preprocessing pipeline for all available tasks, with all
available modes for each task:
```
python3 -m hearpreprocess.runner all --mode all
```

You can instead just call a specific single task
```
python3 -m hearpreprocess.runner task1 --mode all
```
or specific multiple tasks:
```
python3 -m hearpreprocess.runner task1 task2 --mode all
```

Upload to private bucket:
```
gsutil -m cp hear-*.tar.gz gs://hear2021-private/
```

Upload to open bucket:
```
gsutil -m cp hear-*dcase2016_task2*.tar.gz gs://hear2021/open-tasks/
gsutil -m cp hear-*speech_commands*.tar.gz gs://hear2021/open-tasks/
gsutil -m cp hear-*nsynth_pitch*.tar.gz gs://hear2021/open-tasks/
```

Small open tasks can be put in the cloud as follows:
```
gsutil -m cp hear-*dcase2016_task2*small*.tar.gz gs://hear2021/small/
gsutil -m cp hear-*speech_commands*small*.tar.gz gs://hear2021/small/
gsutil -m cp hear-*nsynth_pitch*small*.tar.gz gs://hear2021/small/
```

You can also just run individual tasks:
```
python3 -m hearpreprocess.runner [speech_commands|nsynth_pitch|dcase2016_task2]
```
**_NOTE__**: To run the pipeline on secret tasks please ensure to
initialize, update, and install the `hear2021-secret-tasks` submodule.
This repository is not available for participants. If the submodule
is set up:
- The aforementioned commands will work for secret tasks as
well.
- Running with the task `all` option will trigger all the available
set of open and secret tasks.
- To run individual tasks, please use the corresponding `task` name.
The secret task names are are also hidden and listed in the
`hear2021-secret-tasks` submodule.

Each pipeline will download and preprocess each dataset according
to the following DAG:
* DownloadCorpus
* ExtractArchive
* ExtractMetadata: Create splits over the entire corpus and find
the label metadata for them.
* SubcorpusSplit (subsample each split) => MonoWavSplit => TrimPadSplit => SubcorpusData (symlinks)
* SubcorpusData => {SubcorpusMetadata, ResampleSubcorpus}
* SubcorpusMetadata => MetadataVocabulary
* FinalCombine => TarCorpus => FinalizeCorpus

In terms of sampling:
* We create a 60/20/20 split if train/valid/test does not exist.
* We cap each split at 3/1/1/ hours of audio, defined as
* If further small sampling happens, that chooses a particular
number of audio samples per task.

These commands will download and preprocess the entire dataset. An
intermediary directory defined by the option `luigi-dir`(default
`_workdir`) will be created, and then a final directory defined by
the option `tasks-dir` (default `tasks`) will contain the completed
dataset.

Options:
```
Options:
  --num-workers INTEGER  Number of CPU workers to use when running. If not
                         provided all CPUs are used.
  --sample-rate INTEGER  Perform resampling only to this sample rate. By
                         default we resample to 16000, 22050, 44100, 48000.
  --tmp-dir TEXT         Temporary directory to save all the intermediate
                         tasks (will not be deleted afterwords). (default:
                         _workdir/)
  --tasks-dir TEXT       Directory to save the final task output (default:
                         tasks/)
  --tar-dir TEXT         Directory to save the tar'ed output (default: .)
  --mode TEXT            default, all, or small mode for each task.
  --help                 Show this message and exit.
```

To check the stats of an audio directory:
```
python3 -m hearpreprocess.audio_dir_stats {input folder} {output json file}
```
Stats include: audio_count, audio_samplerate_count, mean meadian
and certain (10, 25, 75, 90) percentile durations.  This is helpful
in getting a quick glance of the audio files in a folder and helps
in decideing the preprocessing configurations.

The pipeline will also generate some stats of the original and
preprocessed data sets, e.g.:
```
speech_commands-v0.0.2/01-ExtractArchive/test_stats.json
speech_commands-v0.0.2/01-ExtractArchive/train_stats.json
speech_commands-v0.0.2/03-ExtractMetadata/labelcount_test.json
speech_commands-v0.0.2/03-ExtractMetadata/labelcount_train.json
speech_commands-v0.0.2/03-ExtractMetadata/labelcount_valid.json
```

### Faster preprocessing, for development

The small flag runs the preprocessing pipeline on a small version
of each dataset stored at [Downsampled HEAR Open
Tasks](https://github.com/neuralaudio/hear2021-open-tasks-downsampled). This
is used for development and continuous integration tests for the
pipeline.

These small versions of the data can be generated
deterministically with the following command:
```
python3 -m hearpreprocess.sampler <taskname>
```

**_NOTE_** : `--mode small` is used to run the task on a
small version of the dataset for development.

### Breaking change for hear-eval

If the open tasks have changed enough to break the downstream CI,
(for example in the heareval repo), the [Preprocessed Downsampled HEAR Open
Tasks](https://github.com/neuralaudio/hear2021-open-tasks-downsampled/tree/main/preprocessed)
should be updated. An example of an obvious breaking changes can be modification of the task configuration.

The version should be bumped up in `hearpreprocess/__init__.py` and the pipeline should
be run for the open tasks with `--mode small` flag

Thereafter, the following command can be used to copy the tarred files produced by running the pipeline for the open tasks to the repo( Please clone the repo )

```
git clone git@github.com:neuralaudio/hear2021-open-tasks-downsampled.git
cp hear-LATEST-speech_commands-v0.0.2-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
cp hear-LATEST-nsynth_pitch-v2.2.3-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
cp hear-LATEST-dcase2016_task2-hear2021-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
cp hear-2021.0.6-speech_commands-v0.0.2-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
cp hear-2021.0.6-nsynth_pitch-v2.2.3-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
cp hear-2021.0.6-dcase2016_task2-hear2021-small-44100.tar.gz ./hear2021-open-tasks-downsampled/preprocessed/
```
