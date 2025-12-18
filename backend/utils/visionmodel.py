from llama_cpp import Llama
from PIL import Image
import numpy as np
from transformers import AutoModel, AutoTokenizer
import torch



# Load the model (ensure you have the correct path to the quantized model)
model_path = "./MiniCPM-Llama3-V-2_5/model/ggml-model-Q4_K_M.gguf"
# model_path = "./MiniCPM-Llama3-V-2_5/model/ggml-model-BF16.gguf"
# model_path = "./MiniCPM-Llama3-V-2_5/mmproj-model-f16.gguf"
# tokenizer = AutoTokenizer.from_pretrained('openbmb/MiniCPM-Llama3-V-2_5-int4', trust_remote_code=True)


image_path = "./image.png"

# Initialize the model with parameters
llm = Llama(model_path=model_path, ctx_size=4096, temperature=0.1, top_p=0.8, top_k=100, repeat_penalty=1.05)

image = Image.open(image_path).convert('RGB')

prompt = f"Describe the content of this image: {image}"
question = 'Describe this image in detail'
msgs = [{"role": "system", "content": "You are an assistant who perfectly describes images."},
        {'role': 'user', 'content': question}]

# Run inference
output = llm(prompt, max_tokens=500)


# response = llm.create_chat_completion(messages=msgs)
# print(response["choices"][0]['message']['content'])

# Display output
print("Image Summary is: ",output["choices"][0]["text"])


# ./minicpmv-cli -m ../MiniCPM-Llama3-V-2_5/model/ggml-model-Q4_K_M.gguf --mmproj ../MiniCPM-Llama3-V-2_5/mmproj-model-f16.gguf -c 4096 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 --image ../image.png  -p "What is in the image?"
