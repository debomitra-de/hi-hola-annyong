# Hi-Hola Architecture

## 1. Purpose

Hi-Hola is an open-source language-learning application focused on
spoken English and Spanish practice. Its architecture connects speech
recognition, conversational response generation, speech synthesis, and
pronunciation assessment to support an interactive learning workflow.

This document describes the main processing pipeline and the
responsibilities of the components currently identified in the project.
It is intended to help contributors understand where data moves and
where changes belong.

## 2. High-level architecture

``` text
                         Learner
                            |
                     Spoken input
                            |
                            v
                 Speech recognition
                    Faster-Whisper
                            |
                    Recognized text
                            |
                            v
              Conversation orchestration
                            |
                            v
                Language model response
                 Ollama / Qwen 2.5
                            |
                  Generated response
                     /          \
                    /            \
                   v              v
          Speech synthesis   Text / response
              Kokoro          presentation
                   |
             Generated audio
                   |
                   v
                 Learner

      Pronunciation assessment is an associated
      learning/feedback path using the learner's
      speech and the relevant target text.
```

The diagram is conceptual. The exact UI framework, transport mechanism,
and deployment topology should be documented here once confirmed from
the implementation.

## 3. Main components

### 3.1 Application interface

The interface is the learner-facing entry point. It collects learner
input, presents recognized text and generated responses, and exposes the
available learning interactions.

The frontend framework and exact interface modules should be added here
after verifying the current application entry point.

### 3.2 Speech recognition --- Faster-Whisper

Faster-Whisper converts the learner's audio input into text. The
recognized text is passed to the conversation flow so that the language
model can respond to what the learner said.

Important considerations: - Handle missing, empty, or unsupported audio
safely. - Surface recognition failures clearly rather than silently
treating them as valid text. - Avoid logging raw audio or personal
content unless necessary and disclosed.

### 3.3 Conversation generation --- Ollama and Qwen

The conversation component sends the recognized text and relevant
conversation context to a language model served through Ollama. The
repository's current interface configuration identifies `qwen2.5:7b` as
the model name.

The model produces a response for the learner. Model availability and
the configured model name must match the local Ollama setup
instructions.

Important considerations: - Keep model configuration outside hard-coded
user-specific settings where practical. - Handle Ollama being
unavailable, the model not being installed, and generation errors. -
Treat model output as generated content; it may be inaccurate and should
not be presented as authoritative instruction in every case.

### 3.4 Speech synthesis --- Kokoro

Kokoro converts the generated response text into audio so the learner
can hear a spoken response.

Important considerations: - Handle synthesis errors and empty response
text. - Keep generated audio handling separate from conversation
generation. - Make clear to the learner when audio generation is
unavailable.

### 3.5 Pronunciation assessment

Hi-Hola includes a pronunciation-assessment path intended to provide
feedback on learner speech. The project uses a Spanish phonemization
component associated with CNAM and its own pronunciation-scoring
implementation.

At a conceptual level, pronunciation assessment compares learner speech
with the relevant target text/phonetic representation and produces
feedback. Contributors should consult the implementation and tests
before changing scoring behavior.

The precise scoring formula, alignment method, thresholds, and output
schema should be documented here only after they are confirmed from the
current implementation. Do not assume a particular metric or claim that
a score is a validated measure of language proficiency.

## 4. End-to-end interaction flow

1.  The learner provides spoken input through the application.
2.  The application passes the audio to the speech-recognition
    component.
3.  Faster-Whisper returns recognized text.
4.  The conversation flow supplies the text and any applicable context
    to the Ollama-hosted Qwen model.
5.  The model generates a response.
6.  The response is presented as text and passed to Kokoro for speech
    synthesis when audio output is requested or enabled.
7.  The application presents the generated audio to the learner.
8.  Where pronunciation practice is used, the assessment path processes
    the learner's speech against the relevant target and returns
    feedback.

The exact ordering and coupling of steps 6--8 may vary with the
implemented interface. Keep this section synchronized with actual
behavior when the pipeline changes.

## 5. Configuration and local dependencies

The application depends on locally configured software/model components,
including: - Python project dependencies declared by the repository. -
Faster-Whisper for speech recognition. - Ollama and the configured Qwen
model for response generation. - Kokoro for speech synthesis. - The
project's pronunciation-assessment dependencies.

Use the repository's setup guide as the source of truth for installation
commands, supported operating systems, environment variables, and model
download instructions: [Setup guide](setup.md).

Do not commit API keys, credentials, local model files, recordings, or
machine-specific configuration.

## 6. Error handling and reliability

Contributors should preserve clear failure behavior across component
boundaries.

  -----------------------------------------------------------------------
  Component               Example failure         Expected behavior
  ----------------------- ----------------------- -----------------------
  Audio input             Missing or invalid      Show a useful
                          audio                   validation message

  Speech recognition      Model error or no       Report the failure; do
                          transcription           not pass fabricated
                                                  text onward

  Ollama / Qwen           Service unavailable or  Explain how to check
                          model missing           the local model/service

  Speech synthesis        Empty text or synthesis Keep the text response
                          failure                 usable when possible

  Pronunciation           Missing target or       Return a clear error
  assessment              invalid input           instead of a misleading
                                                  score
  -----------------------------------------------------------------------

Avoid exposing stack traces or sensitive local paths in learner-facing
messages. Preserve diagnostic details in appropriate developer logs.

## 7. Testing

The repository uses pytest for automated tests and Ruff for
linting/format checks. The GitHub Actions workflow runs project checks
for repository changes.

When modifying a pipeline component: - Add or update focused unit
tests. - Test invalid and missing inputs. - Mock heavyweight
model/service boundaries in unit tests where appropriate. - Add
integration tests only when they can run reliably in the project's
supported environment. - Update this document if component
responsibilities or data flow change.

Run the commands documented in the repository setup guide and
`pyproject.toml`; do not assume commands that are not configured by the
project.

## 8. Design boundaries and future documentation

The following implementation details should be filled in as the codebase
evolves: - Confirmed frontend framework and application entry point. -
Exact modules/functions connecting the speech, LLM, TTS, and assessment
stages. - Audio formats, sample rates, and payload schemas at component
boundaries. - Conversation-context storage and lifecycle. -
Pronunciation scoring method and interpretation. - Supported languages,
voices, and model versions. - Deployment/runtime topology, if deployment
is added.

Architecture documentation should describe implemented behavior, not
planned features. Proposed changes belong in issues or the roadmap.
