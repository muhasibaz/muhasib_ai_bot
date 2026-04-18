from rag import add_document

with open("tax_code.txt", "r", encoding="utf-8") as f:
    text = f.read()

# делим на части
chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

for i, chunk in enumerate(chunks):
    add_document(chunk, f"tax_{i}")
