import os
import sys
import base64
from io import BytesIO
import tempfile
import requests
import urllib.request
import gradio as gr
from openai import OpenAI
from PIL import Image

# Set up directories and file paths
script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "application_config.txt")

# API Key Management
def save_api_key(api_key):
    with open(config_file, "w") as file:
        file.write(api_key)
    return f"API key saved successfully to \"{config_file}\". Please refresh the browser to continue."

def load_api_key():
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return file.read().strip()
    return None

# OpenAI Client Initialization
def initialize_client():
    api_key = load_api_key()
    if api_key:
        return OpenAI(api_key=api_key)
    return None

client = None

# Image Captioning
def caption_img(url):
    caption_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Caption this image in a maximum of six words."},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }
        ],
        max_tokens=20,
    )
    return caption_response.choices[0].message.content

# DALL-E Image Generation
def dalle_img_gen(usr_prompt, size, enhance_prompt, format_selection):
    if enhance_prompt == "No":
        usr_prompt = f"I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS: \"{usr_prompt}\""
    
    response = client.images.generate(
        prompt=usr_prompt,
        model="dall-e-3",
        size=size,
        n=1,
    )

    img_url = response.data[0].url
    image_file = download_image(img_url)
    cap = caption_img(img_url)
    tmp_file_path = save_image(image_file, format_selection)
    
    return image_file, cap, tmp_file_path

def download_image(url):
    with urllib.request.urlopen(url) as response:
        image_data = response.read()
    return Image.open(BytesIO(image_data))

def save_image(image, format_selection):
    output = BytesIO()
    image.save(output, format=format_selection.upper())
    output.seek(0)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_selection.lower()}") as tmp_file:
        tmp_file.write(output.getbuffer())
        return tmp_file.name

# Image Processing
def process_img(image, image_url):
    if image:
        return handle_local_image(image)
    if image_url:
        return handle_image_url(image_url)
    return "Error: No image provided via file upload or URL."

def handle_local_image(image):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_file.write(image)
    temp_file.close()
    
    public_image_url = upload_image_to_fileio(temp_file.name)
    os.unlink(temp_file.name)
    
    return public_image_url

def handle_image_url(image_url):
    if os.path.exists(image_url):
        return upload_image_to_fileio(image_url)
    
    try:
        response = requests.head(image_url)
        if response.status_code == 200:
            return image_url
        return "Error: Image URL is not accessible."
    except requests.exceptions.RequestException as e:
        return f"Error: Invalid image URL. Details: {str(e)}"

def upload_image_to_fileio(image_path, expiration="1h"):
    with open(image_path, 'rb') as image_file:
        response = requests.post(
            'https://file.io',
            files={'file': image_file},
            data={'expires': expiration}
        )
    if response.status_code == 200:
        return response.json()['link']
    raise Exception(f"Failed to upload image: {response.status_code} {response.text}")

# Image-to-Text Interaction
def img_to_txt(img_url, usr_prompt, max_tokens, temperature, chat_history):
    model = "gpt-4o"
    
    messages = build_chat_history(chat_history)
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": usr_prompt},
            {"type": "image_url", "image_url": {"url": img_url}}
        ]
    })

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False
    )
    
    assistant_message = response.choices[0].message.content
    chat_history.append([usr_prompt, assistant_message])
    return chat_history, chat_history

def build_chat_history(chat_history):
    messages = [
        {"role": "system", "content": "You are a helpful, creative, and honest chatbot."}
    ]
    for user_msg, assistant_msg in chat_history:
        messages.append({"role": "user", "content": [{"type": "text", "text": user_msg}]})
        messages.append({"role": "assistant", "content": [{"type": "text", "text": assistant_msg}]})
    return messages

def reset_chat():
    return []

# Gradio Interface Functions

def img_to_img(image, image_url, usr_prompt, size, format_selection):
    img_url = process_img(image, image_url)
    
    if "Error" in img_url:
        return None, img_url, None
    
    refined_prompt = generate_refined_prompt(img_url, usr_prompt)
    img_res = generate_image_from_prompt(refined_prompt, size)
    
    image_file = download_image(img_res)
    caption = caption_img(img_res)
    tmp_file_path = save_image(image_file, format_selection)
    
    return image_file, caption, tmp_file_path

def generate_refined_prompt(img_url, usr_prompt):
    prompt_model = "gpt-4o-mini"
    
    messages = [
        {"role": "system", "content": "You are a master prompt generator. Generate excellent and creative prompts based on the user prompt and the image, which can then be passed onto an image generation model like DALL-E 3 to create that image. Ensure that the user's prompt is used as an absolute guideline in generating every prompt."},
        {"role": "user", 
         "content": [
            {"type": "text", "text": usr_prompt},
            {"type": "image_url", "image_url": {"url": img_url}}
        ]}
    ]

    prompt_res = client.chat.completions.create(
        model=prompt_model,
        messages=messages,
        max_tokens=300,
        temperature=0.9,
    )
    return prompt_res.choices[0].message.content

def generate_image_from_prompt(prompt, size):
    img_model = "dall-e-3"
    img_res = client.images.generate(
        model=img_model,
        prompt=prompt,
        n=1,
        size=size,
        response_format="url"
    )
    return img_res.data[0].url


# Custom Print Filter
def filter_print(*args, **kwargs):
    output = " ".join(map(str, args))
    if "To create a public link, set `share=True` in `launch()`" not in output:
        original_print(output, **kwargs)

original_print = print
title = "DALLE-3 MASTERWARE +"
custom_css = """
    footer {
        display: none !important;
    }
    body, html {
        height: 100%;
        margin: 0;
        display: flex;
        flex-direction: column;
    }
    .gradio-container {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .custom-footer-container {
        text-align: center;
        padding-top: 20px;
        padding-bottom: 20px;
        background-color: var(--bg);
        color: var(--col);
        border-top: 1px solid var(--bg);
        width: 100%;
    }

    @media (prefers-color-scheme: dark) {
        .custom-footer-container {
            background-color: var(--bg-dark);
            color: var(--col-dark);
            border-top-color: var(--bg-dark);
        }
    }
"""
custom_html = """
<div class="custom-footer-container">
    <style type="text/css">
    .centerContent {{
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .centerContent img {{
        margin-right: 10px;
    }}
    </style>
    <div class="centerContent">
        <img src="data:image/x-icon;base64,{image_data}" alt="PSYGNEX Logo" height="50" width="50">
        <h1 style="display:inline;">Built by PSYGNEX</h1>
    </div>
</div>
"""

def load_encoded_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

encoded_image = load_encoded_image(os.path.join(script_dir, "static", "PSYGNEX_transbg.ico"))
custom_html = custom_html.format(image_data=encoded_image)

def text_to_image_tab():
    prompt_input = gr.Textbox(label="Prompt")
    size_input = gr.Radio(choices=["1024x1024", "1024x1792", "1792x1024"], label="Select Image Size", value="1024x1024")
    enhance_prompt_input = gr.Radio(choices=["Yes", "No"], label="Prompt Enhancement", value="Yes")
    format_input = gr.Dropdown(choices=["PNG", "JPEG", "WEBP"], label="Select Download Format", value="WEBP")
    generate_button = gr.Button("Generate Image")
    regenerate_button = gr.Button("Regenerate Image")
    image_output = gr.Image(label="Generated Image")
    caption_output = gr.TextArea(label="Caption")
    download_output = gr.File(label="Download Image")
    generate_button.click(fn=dalle_img_gen, inputs=[prompt_input, size_input, enhance_prompt_input, format_input], outputs=[image_output, caption_output, download_output])
    regenerate_button.click(fn=dalle_img_gen, inputs=[prompt_input, size_input, enhance_prompt_input, format_input], outputs=[image_output, caption_output, download_output])
    
def img_img_gen_interface():
    with gr.Blocks() as img_img_chat_tab:
        image_input = gr.File(label="Upload an Image (JPG, PNG, WEBP)", type="binary")
        image_url_input = gr.Textbox(label="Or enter an image URL")
        size_input = gr.Radio(choices=["1024x1024", "1024x1792", "1792x1024"], label="Select Image Size", value="1024x1024")
        image_out_type = gr.Radio(choices=["PNG", "JPEG", "WEBP"], label="File type required", value="WEBP")
        usr_prompt = gr.Textbox(label="Enter your prompt. How do you want the image to be?")
        submit_button = gr.Button("Generate Image")
        regen_button = gr.Button("Regenerate Image")
        image_out = gr.Image(label="Generated Image appears here")
        image_caption = gr.TextArea(label="Caption")
        image_down = gr.File(label="Download Image")
        clear_out = gr.ClearButton([image_out_type, size_input, image_out, image_caption, usr_prompt, image_down])
        
        submit_button.click(fn=img_to_img, inputs=[image_input, image_url_input, usr_prompt, size_input, image_out_type], outputs=[image_out, image_caption, image_down])
        regen_button.click(fn=img_to_img, inputs=[image_input, image_url_input, usr_prompt, size_input, image_out_type], outputs=[image_out, image_caption, image_down])
        
    return img_img_chat_tab

def chat_interface_tab():
    with gr.Blocks() as chat_tab:
        img_input = gr.File(label="Upload an Image (JPG, PNG, WEBP)", type="binary")
        img_url_input = gr.Textbox(label="Or enter an image URL")
        max_tokens = gr.Slider(1, 4096, label="Max Tokens", value=1024)
        temperature = gr.Slider(0, 1, label="Temperature", value=0.7)
        chatbot = gr.Chatbot(label="Chatbot")
        usr_prompt = gr.Textbox(label="Enter your prompt or question")
        gr.Examples([["What's this image about?"], ["Generate a story taking cue from the image"], ["Print the image contents"]], usr_prompt, label="Something to get started with...")
        submit_button = gr.Button("Submit")
        clear = gr.ClearButton([chatbot, usr_prompt])
        stop_button = gr.Button("Clear Session Context")

        chat_history = gr.State([])

        def handle_submission(image, url, prompt, max_tokens, temperature, chat_history):
            img_url = process_img(image, url)
            if "Error" in img_url:
                return img_url, chat_history
            return img_to_txt(img_url, prompt, max_tokens, temperature, chat_history)

        submit_button.click(handle_submission, inputs=[img_input, img_url_input, usr_prompt, max_tokens, temperature, chat_history], outputs=[chatbot, chat_history])
        stop_button.click(reset_chat, outputs=chat_history)
    return chat_tab

def main_app():
    global client
    client = initialize_client()
    with gr.Blocks(title=title, css=custom_css) as app:
        with gr.Column(elem_classes=["content-wrapper"]):
            gr.Markdown("## DALLE-3 MASTERWARE +")
            gr.Markdown("AN OPENAI DALL-E-3 BASED INFERENCE GUI")
            with gr.Tab("Text-to-Image"):
                text_to_image_tab()
            with gr.Tab("Image-to-Image"):
                img_img_gen_interface()
            with gr.Tab("Image-to-Text"):
                chat_interface_tab()
            gr.HTML(custom_html)
    
    try:
        sys.modules['builtins'].print = filter_print
        app.launch(favicon_path=os.path.join(script_dir, "static", "PSYGNEX_transbg.ico"), share=False)
    finally:
        sys.modules['builtins'].print = original_print

def on_submit(api_key):
    message = save_api_key(api_key)
    return message, gr.update(visible=False)

def ask_for_api_key():
    with gr.Blocks(title=title, css=custom_css) as app:
        with gr.Row():
            gr.Markdown("## Enter Your OpenAI API Key")
        api_key_input = gr.Textbox(label="OpenAI API Key", type="password")
        submit_button = gr.Button("Submit")
        output_message = gr.Markdown()
        gr.HTML(custom_html)
        
        submit_button.click(on_submit, inputs=[api_key_input], outputs=[output_message, submit_button])

        try:
            sys.modules['builtins'].print = filter_print
            app.launch(favicon_path=os.path.join(script_dir, "static", "PSYGNEX_transbg.ico"), share=False)
        finally:
            sys.modules['builtins'].print = original_print

if load_api_key() is None:
    ask_for_api_key()
else:
    main_app()
