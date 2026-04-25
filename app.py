import os
from flask import Flask, render_template, request, redirect, send_file
from cryptography.fernet import Fernet

app = Flask(__name__)

# =============================
# CONFIG
# =============================
BLOCK_SIZE = 1024
STORAGE_DIR = "cloud_storage"
KEY_FILE = "secret.key"

os.makedirs(STORAGE_DIR, exist_ok=True)

# =============================
# KEY MANAGEMENT
# =============================
def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return key

cipher = Fernet(load_key())

# =============================
# CORE FUNCTIONS
# =============================
def encrypt(data):
    return cipher.encrypt(data)

def decrypt(data):
    return cipher.decrypt(data)

def split_file(data):
    return [data[i:i+BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]

def save_blocks(filename, blocks):
    for i, block in enumerate(blocks):
        with open(f"{STORAGE_DIR}/{filename}_block_{i}", "wb") as f:
            f.write(block)

def read_blocks(filename):
    data = b""
    i = 0
    while True:
        path = f"{STORAGE_DIR}/{filename}_block_{i}"
        if not os.path.exists(path):
            break
        with open(path, "rb") as f:
            data += f.read()
        i += 1
    return data

def delete_file_blocks(filename):
    for f in os.listdir(STORAGE_DIR):
        if f.startswith(filename + "_block_"):
            os.remove(os.path.join(STORAGE_DIR, f))

def list_files():
    files = {}
    for f in os.listdir(STORAGE_DIR):
        if "_block_" in f:
            name = f.split("_block_")[0]
            size = os.path.getsize(os.path.join(STORAGE_DIR, f))
            files[name] = files.get(name, 0) + size
    return [(n, round(s/1024, 2)) for n, s in files.items()]

# =============================
# ROUTES
# =============================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if file:
        data = file.read()
        encrypted = encrypt(data)
        blocks = split_file(encrypted)
        save_blocks(file.filename, blocks)
    return redirect("/files")

@app.route("/files")
def files():
    return render_template("files.html", files=list_files())

@app.route("/download/<filename>")
def download(filename):
    encrypted = read_blocks(filename)
    decrypted = decrypt(encrypted)

    temp_path = f"temp_{filename}"
    with open(temp_path, "wb") as f:
        f.write(decrypted)

    return send_file(temp_path, as_attachment=True)

@app.route("/delete/<filename>")
def delete(filename):
    delete_file_blocks(filename)
    return redirect("/files")

# =============================
# MAIN (RENDER READY)
# =============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # Render uses dynamic port
    app.run(host="0.0.0.0", port=port)