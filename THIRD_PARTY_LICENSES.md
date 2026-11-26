# Third-party licenses

The project is licensed under the GNU Affero General Public License,
version 3 or (at your option) any later version. This license applies to
project-authored code; it does not change the licenses of third-party
software, model weights, or system tools.

This is an initial inventory of direct dependencies and separately fetched
assets, not a complete license scan of every transitive package or binary.
The lockfiles (`uv.lock` and `ui/package-lock.json`) identify dependency
versions. Preserve upstream copyright and license notices when redistributing
third-party components, and verify the license for the exact version and
distribution you use.

## Python dependencies

| Component | License |
| --- | --- |
| av | BSD-3-Clause |
| FastAPI | MIT |
| Faster-Whisper | MIT |
| Kokoro | Apache-2.0 |
| phonemizer | GPL-3.0-or-later |
| Pydantic | MIT |
| [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright) | AGPL-3.0 or a commercial license |
| pyspellchecker | MIT |
| python-multipart | Apache-2.0 |
| SciPy | BSD |
| sounddevice | MIT |
| soundfile | BSD |
| PyTorch | Multiple licenses; see the notices included with its distribution |
| Transformers | Apache-2.0 |
| Uvicorn | BSD-3-Clause |
| espeakng-loader | MIT (loader code); bundles eSpeak NG under GPL-3.0-or-later |

Development dependencies and transitive dependencies have their own licenses
and notices. The Python license scan also reported `num2words` under an LGPL
license; verify its exact version and license text in the resolved environment.

## Frontend dependencies

The Python license scan does not cover the JavaScript dependencies declared in
`ui/package.json`. Check the license metadata and notices for packages in
`ui/package-lock.json` before redistributing a bundled frontend.

## Models and external tools

Model weights are not covered by this project's license and keep their own
licenses. Models and external tools are downloaded or installed separately.

| Component | License |
| --- | --- |
| [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) (`qwen2.5:7b`) | Apache-2.0 |
| [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | Qwen Research License; not used by the current setup, research/non-commercial terms |
| [Whisper `small`](https://huggingface.co/Systran/faster-whisper-small) via Faster-Whisper | MIT |
| [Whisper `medium`](https://huggingface.co/Systran/faster-whisper-medium) via Faster-Whisper | MIT |
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-2.0 |
| [CNAM Spanish phonemizer](https://huggingface.co/Cnam-LMSSC/wav2vec2-spanish-phonemizer) | MIT per its model card; upstream base-model license not independently checked |
| [Ollama](https://github.com/ollama/ollama) | MIT |
| [FFmpeg](https://ffmpeg.org/legal.html) | LGPL-2.1-or-later or GPL, depending on build configuration |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng) | GPL-3.0-or-later |
| [PortAudio](https://github.com/PortAudio/portaudio) | MIT-style |
| [espeakng-loader](https://pypi.org/project/espeakng-loader/) | MIT loader code; bundles eSpeak NG under GPL-3.0-or-later |

The model license applies to the specific model artifact, not to the loader
library. Check model cards and notices for updates to these terms.
