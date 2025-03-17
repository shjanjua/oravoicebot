# oravoicebot

A simple voice chatbot powered by Oracle Cloud Infrastructure (OCI) services. This project combines Speech-to-Text (STT), a Large Language Model (LLM), and Text-to-Speech (TTS) to create a conversational AI that you can interact with using your voice.

## Features

- **Voice Interaction:** Speak to the chatbot and hear its responses.
- **OCI Powered:** Leverages OCI's Generative AI and Speech services for intelligent conversations.
- **Customizable LLM:** Easily configure the LLM model to use via environment variables.
- **Streaming Responses:** (Partially implemented) The code is set up for streaming responses from the LLM, which can be further enhanced for a more interactive experience.
- **Simple Setup:**  Uses `.env` file for easy configuration of OCI credentials and service parameters.

## Prerequisites

Before you begin, ensure you have the following:

1. **Oracle Cloud Infrastructure Account:** You'll need an active OCI account to use the Generative AI and Speech services.
2. **OCI API Key:**  Generate and configure an OCI API key. Refer to the [OCI documentation](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm) for instructions on how to set up your API key and OCI CLI configuration file.
3. **Python 3.8+:**  Make sure you have Python 3.8 or a later version installed on your system.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shjanjua/oravoicebot.git
   cd oravoicebot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `env.sample` to `.env`:
     ```bash
     cp env.sample .env
     ```
   - **Edit the `.env` file** and fill in the required values:
     - `COMPARTMENT_ID`: Your OCI Compartment OCID where you have access to Generative AI and Speech services.
     - `VOICE_ID`: The voice to use for Text-to-Speech.  While the code currently defaults to "Annabelle" voice in `TTS.py`, this variable is defined in `.env` and can be used for future configuration.
     - `MODEL_ID`: The ID of the LLM model you want to use. The default is `meta.llama-3.3-70b-instruct`.
     - `REGION`: Your OCI region (e.g., `uk-london-1`, `us-phoenix-1`). Make sure the region supports OCI Generative AI and Speech/STT services.  Note that TTS currently primarily works from `us-phoenix-1`.

   **Example `.env` file:**
   ```
   COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaa6gapyx7754dtzpcq3x6h5fmdqjboryka6e2vndc7uds5pmqsqvuq"
   VOICE_ID = "Annabelle" # Currently hardcoded in TTS.py, but can be used for future config
   MODEL_ID = "meta.llama-3.3-70b-instruct"
   REGION = "uk-london-1"
   ```

## Usage

Run the voice chatbot:

```bash
python voicechatbot.py
```

The chatbot will start, and you should hear "Say something!".  Start speaking, and the chatbot will transcribe your speech, send it to the LLM, and speak back the LLM's response.

To stop the chatbot, press `Ctrl+C`.

## Environment Variables

| Variable        | Description                                                                    | Default Value                |
|-----------------|--------------------------------------------------------------------------------|------------------------------|
| `COMPARTMENT_ID` | OCID of your OCI Compartment. Required for accessing OCI services.              | None                         |
| `VOICE_ID`       | Voice ID for Text-to-Speech. Currently not directly used, defaults to Annabelle in code. | "Bob"                        |
| `MODEL_ID`       | ID of the LLM model to use.                                                     | `meta.llama-3.3-70b-instruct` |
| `REGION`         | OCI region where your services are located.                                    | `us-phoenix-1`               |

**Important Notes:**

- **OCI Configuration:** Ensure your OCI CLI configuration file (`~/.oci/config`) and API key are correctly set up with the necessary permissions to access OCI Generative AI and Speech services in your specified compartment and region.
- **Region Compatibility:** Double-check that the `REGION` you set supports both OCI Generative AI and Speech services.  Text-to-Speech (TTS) functionality may be limited to specific regions like `us-phoenix-1`.
- **Microphone Access:**  The script requires access to your microphone. Ensure your system's permissions are configured to allow Python to access your microphone.

## Dependencies

- `pyaudio`
- `oci`
- `aiohttp`
- `requests`
- `oci.ai-speech-realtime`
- `python-dotenv`

These dependencies are listed in `requirements.txt` and can be installed using `pip install -r requirements.txt`.
