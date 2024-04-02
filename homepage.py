from flask import Flask, request, render_template, redirect, url_for
import os
import cv2
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import mysql.connector
# from werkzeug.utils import secure_filename
import base64
from PIL import Image
import sys


# Database 
mydb = mysql.connector.connect(
  host="localhost",
  user="comSecure",
  password="ict555",
  database="imgbDB"
)

app = Flask(__name__)

@app.route('/')
def index():
    # Create a cursor object
    return render_template('index.html')

@app.route('/encrypt_decrypt', methods=['POST'])

# def encrypt_decrypt():
#     # Check if the request contains a file
#     if 'file' not in request.files:
#         return 'No file in the request'

#     file = request.files['file']

#     # Check if a file was uploaded
#     if file.filename == '':
#         return 'No file selected'

#     # Read the image file
#     img_bytes = file.read()

#     # Encrypt the image
#     encrypted_img = encrypt_image(img_bytes)

#     # Decrypt the image
#     decrypted_img = decrypt_image(encrypted_img)

#     return decrypted_img

# can use this ver
def encrypt_image(img_bytes):
    mode = AES.MODE_CBC
    key_size = 32
    iv_size = AES.block_size if mode == AES.MODE_CBC else 0

    # Load original image
    image_orig = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), -1)
    row_orig, column_orig, depth_orig = image_orig.shape

    # print("Original image dimensions:", row_orig, "x", column_orig, "x", depth_orig)

    # Encrypt
    key = get_random_bytes(key_size)
    iv = get_random_bytes(iv_size)
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    image_orig_bytes_padded = pad(img_bytes, AES.block_size)

    # Encrypt the padded image bytes
    ciphertext = cipher.encrypt(image_orig_bytes_padded)

    # Convert ciphertext bytes to encrypted image data
    padded_size = len(image_orig_bytes_padded)
    expected_size = row_orig * column_orig * depth_orig
    void = expected_size - len(iv) - padded_size
    iv_ciphertext_void = iv + ciphertext + bytes([0] * void)
    
    print("iv_ciphertext_void size:", len(iv_ciphertext_void))
    print("Expected size:", expected_size)

    reshaped_array = np.frombuffer(iv_ciphertext_void, dtype=np.uint8).reshape(row_orig, column_orig, depth_orig)

    # Encode the reshaped array to a JPEG image
    success, encoded_img = cv2.imencode('.jpg', reshaped_array)

    if not success:
        return b'Encoding failed'

    # Convert encoded image data to bytes
    encrypted_img = encoded_img.tobytes()

    # Concatenate IV and ciphertext
    encrypted_img = iv + ciphertext

    return encrypted_img, key


def decrypt_image(encrypted_img):
    mode = AES.MODE_CBC
    key_size = 32
    iv_size = AES.block_size if mode == AES.MODE_CBC else 0

    # Convert encrypted image data to ciphertext bytes
    image_encrypted = cv2.imdecode(np.frombuffer(encrypted_img, np.uint8), -1)
    row_encrypted, column_orig, depth_orig = image_encrypted.shape
    row_orig = row_encrypted - 1
    encrypted_bytes = image_encrypted.tobytes()
    iv = encrypted_bytes[:iv_size]
    image_orig_bytes_size = row_orig * column_orig * depth_orig
    padded_size = (image_orig_bytes_size // AES.block_size + 1) * AES.block_size - image_orig_bytes_size
    encrypted = encrypted_bytes[iv_size: iv_size + image_orig_bytes_size + padded_size]

    # Decrypt
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    decrypted_image_bytes_padded = cipher.decrypt(encrypted)
    decrypted_image_bytes = unpad(decrypted_image_bytes_padded, AES.block_size)

    # Convert bytes to decrypted image data
    decrypted_image = cv2.imdecode(np.frombuffer(decrypted_image_bytes, np.uint8), -1)

    # Convert image data to bytes
    _, img_bytes = cv2.imencode('.jpg', decrypted_image)

    return img_bytes.tostring()

@app.route('/image/<int:image_id>')
def display_image(image_id):
    # Fetch image data from the database
    cursor = mydb.cursor()
    query = "SELECT encryptedImg FROM images WHERE imageID = %s"
    cursor.execute(query, (image_id,))
    result = cursor.fetchone()

    if result is None:
        return 'Image not found'

    image_data = result[0]  # Assuming the first column contains the image data

    # Convert binary data to Base64 encoding
    encoded_image = base64.b64encode(image_data).decode('utf-8')

    # Render HTML template with embedded image
    return render_template('index.html', image_data=encoded_image)


@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the POST request has a file part
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return 'No selected file'

    # Save the uploaded file to the 'uploads' directory
    upload_dir = os.path.join(app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    # filename = secure_filename(file.filename)  # Use Werkzeug's secure_filename to sanitize the filename
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    # Log the file path for debugging
    print("File saved to:", file_path)

    try:
        # Read binary data from file
        with open(file_path, "rb") as file:
            image_data = file.read()
    except FileNotFoundError as e:
        return f'Error: {e}'
    
    encrypted_img, key = encrypt_image(image_data)
    
    # Prepare the INSERT query
    insert_query = 'INSERT INTO images (Img, encryptedImg, keyImg) VALUES (%s, %s, %s)'

    # Create a cursor object to execute SQL queries
    cursor = mydb.cursor()

    # Execute the INSERT statement with the BLOB data
    cursor.execute(insert_query, (image_data, encrypted_img, key,))

    # Commit the transaction
    mydb.commit()

    # Encode image data and encrypted image data to Base64
    encoded_image_data = base64.b64encode(image_data).decode('utf-8')
    encoded_encrypted_img = base64.b64encode(encrypted_img).decode('utf-8')


    print('File uploaded successfully: {}'.format(file_path))
    # return 'File uploaded successfully: {}'.format(file_path)
    # return redirect(url_for('index'))
    return render_template('index.html', upload_file=True, image_data=encoded_image_data, encryptedImage=encoded_encrypted_img)

if __name__ == '__main__':
    app.run(debug=True)
    