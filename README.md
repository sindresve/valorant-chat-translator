# Valorant Chat Translator

This project translates in-game Valorant chat messages into your
preferred language.\
It uses OCR (optical character recognition) to detect text in
screenshots and then translates it automatically.

------------------------------------------------------------------------

## 🚀 Setup Instructions

### 1. Clone the repository

``` bash
git clone https://github.com/sindresve/valorant-chat-translator.git
cd valorant-chat-translator
```

### 2. Download OCR Models

This project requires two OCR model files from Hugging Face:

-   `craft_mlt_25k.pth`
-   `cyrillic_g2.pth`

Download them and place them inside the **`models/`** folder (create the
folder if it doesn't exist).

> 💡 If you don't already have the files, search Hugging Face for
> **CRAFT OCR** and **Cyrillic text recognition**.\
> Example sources:\
> - [CRAFT model](https://huggingface.co/zeusey/CRAFT-pytorch)\
> - [Cyrillic recognition model](https://huggingface.co/)

After downloading, your project should look like this:

    valorant-chat-translator/
    │
    ├── models/
    │   ├── craft_mlt_25k.pth
    │   └── cyrillic_g2.pth
    │
    ├── main.py
    ├── requirements.txt
    └── ...

### 3. Install dependencies

It's recommended to use a virtual environment.

``` bash
python3 -m venv venv
venv\Scripts\activate    # On Windows

pip install -r requirements.txt
```

### 4. Run the program

``` bash
python3 main.py
```
