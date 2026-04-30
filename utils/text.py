import tiktoken
def get_tokenizer(model:str):
    try:
        return tiktoken.get_encoding(model).encode
    except Exception as e:
        encoding= tiktoken.get_encoding("cl100k_base")
        return encoding.encode
    

def count_tokens(text:str,model:str)->int:
    tokenizer = get_tokenizer(model)

    if tokenizer:
        return len(tokenizer(text))
    pass

def estimate_tokens(text:str)->int:
    # Simple heuristic: 1 token ~ 4 characters
    return max(1, len(text) // 4)