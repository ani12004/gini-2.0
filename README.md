# Gini 2.0 - AI Misinformation Detector Bot for Telegram

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)

Gini 2.0 is an intelligent Telegram bot powered by the Google Gemini API. It serves as a multi-purpose assistant, capable of both conversational chat and analyzing text for potential misinformation, scams, or fake news, with a focus on the Indian context.

## ✨ Key Features

-   🤖 **Conversational AI:** Chat directly with the bot for a powerful, general-purpose AI assistant experience.
-   🔎 **Misinformation Detector:** Use the `/search` command to analyze text or links for red flags. The bot provides a confidence score, a summary of its findings, and a list of potential red flags.
-   📝 **Complaint Generation:** For content flagged as high-risk ("Red Flag"), the bot provides a pre-formatted complaint text that can be used for reporting.
-   🇮🇳 **Bilingual Summaries:** Analysis results are provided with simple summaries in both English and Hindi.

## 🚀 Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

-   Python 3.9 or higher
-   A Telegram Bot Token
-   A Google Gemini API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ani12004/gini-2.0.git](https://github.com/ani12004/gini-2.0.git)
    cd gini-2.0
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your environment variables:**
    -   Create a file named `.env` in the root of the project.
    -   Add your secret keys to it like this:
        ```env
        TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
        GEMINI_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY_HERE"
        ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## 💬 How to Use

Interact with the bot on Telegram using the following commands:

-   **/start** or **/help**: Displays the welcome message and instructions.
-   **/search** `<text to analyze>`: Submits your text to the AI for misinformation analysis. The bot will reply with a detailed breakdown.
-   **/complaint**: After a "Red Flag" result from `/search`, use this command to get the pre-formatted complaint text.
-   **Any other message**: Sending any other text message will engage the general conversational chat mode.

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.
