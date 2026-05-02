import tiktoken
def get_tokenizer(model:str):
    try:
        return tiktoken.get_encoding(model).encode
    except Exception as e:
        encoding= tiktoken.get_encoding("cl100k_base")
        return encoding.encode
    

def count_tokens(text:str,model:str="gpt-4")->int:
    tokenizer = get_tokenizer(model)

    if tokenizer:
        return len(tokenizer(text))
    pass

def estimate_tokens(text:str)->int:
    # Simple heuristic: 1 token ~ 4 characters
    return max(1, len(text) // 4)



    
def truncate_text(
    text: str,
    model: str,
    max_tokens: int,
    suffix: str = "\n... [truncated]",
    preserve_lines: bool = True,
):    
    current_tokens = count_tokens(text, model)
    if current_tokens <= max_tokens:
        return text
    suffix_tokens = count_tokens(suffix, model)
    target_tokens = max_tokens - suffix_tokens

    if target_tokens <= 0:
        return suffix
        
    if preserve_lines:
        return _truncate_by_lines(text, target_tokens, suffix, model)
    
    else:
        return _truncate_by_chars(text, model, target_tokens, suffix)

def _truncate_by_lines(text: str, target_tokens: int, suffix: str, model: str) -> str:
    lines = text.split("\n")
    result_lines = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(line + "\n", model)  # include newline in token count
        if current_tokens + line_tokens > target_tokens:
            break
        result_lines.append(line)
        current_tokens += line_tokens

    
    if not result_lines:
        return _truncate_by_chars(text, model, target_tokens, suffix   )

    return "\n".join(result_lines) + suffix

def _truncate_by_chars(text:str, model:str, target_tokens:int, suffix:str)->str:
    low, high = 0, len(text)

    while low < high:
        mid = (low + high + 1) // 2
        if count_tokens(text[:mid], model) <= target_tokens:
            low = mid
        else:
            high = mid - 1

    return text[:low] + suffix