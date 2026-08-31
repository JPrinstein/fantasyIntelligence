import json

def save_chunks(chunks,path):
    with open(path,"w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=2)

def load_chunks(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)