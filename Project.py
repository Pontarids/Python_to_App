# ===[1] IMPORT MODULES===
import cv2
import torch
import easyocr
import joblib
import numpy as np
import re
from keras_facenet import FaceNet
from PIL import Image
from IPython.display import display

# ===[2] IMPORT FIREBASE ADMIN SDK===
import firebase_admin
from firebase_admin import credentials, initialize_app, storage, db
import time
import os

# ===[3] INIT FIREBASE===
if not firebase_admin._apps:
    cred = credentials.Certificate("/content/drive/MyDrive/service-account.json")
    # Tambahkan databaseURL untuk akses Realtime Database
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'detection-app-f3849',
        'databaseURL': 'https://detection-app-f3849-default-rtdb.firebaseio.com/'  # Ganti dengan URL Realtime Database Anda
    })
else:
    print("[INFO] Firebase app already initialized.")

# ===[4] MUAT MODEL===
print("[INFO] Memuat model YOLOv5, FaceNet, OCR, dan SVM...")
yolo_model = torch.hub.load('ultralytics/yolov5', 'custom',
                            path='/content/drive/MyDrive/Ardian12/yolov5/hasil_training/percobaan/weights/best.pt',
                            force_reload=False)

face_embedder = FaceNet()
svm_model = joblib.load("/content/drive/MyDrive/Ardian12/FaceNet/c_svm_model.pkl")
ocr_reader = easyocr.Reader(['en'])
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

authorized_plates = ["N3752EBZ", "N3752EB", "N3752", "3752"]  # Plat yang diizinkan

# ===[5] FUNGSI OCR PLAT===
def recognize_plate(cropped_img):
    results = ocr_reader.readtext(cropped_img)
    for (bbox, text, conf) in results:
        if conf > 0.3:
            text = text.strip().upper()
            print(f"[INFO] OCR: {text} (conf={conf:.2f})")
            return text
    print("[WARNING] OCR gagal mengenali plat.")
    return None

# ===[6] FUNGSI VERIFIKASI WAJAH (HAAR + FACENET + SVM)===
def verify_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    if len(faces) == 0:
        print("[WARNING] Tidak ada wajah terdeteksi.")
        return False

    for (x, y, w, h) in faces:
        face_roi = image[y:y + h, x:x + w]
        face_rgb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
        face_rgb = cv2.resize(face_rgb, (160, 160))

        emb = face_embedder.embeddings([face_rgb])[0]
        prediction = svm_model.predict([emb])
        print("[INFO] Hasil verifikasi wajah:", "✅ Dikenali" if prediction == 1 else "❌ Tidak dikenali")
        return prediction == 1

# ===[7] PROSES UTAMA===
def test_pipeline(frame_bgr):
    rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = yolo_model(rgb_frame)
    detections = results.pandas().xyxy[0]

    if detections.empty:
        print("[WARNING] Tidak ada objek terdeteksi.")
        return

    print("[INFO] Objek terdeteksi:", detections['name'].tolist())

    for _, row in detections.iterrows():
        label = row['name'].lower()
        x1, y1, x2, y2 = map(int, [row['xmin'], row['ymin'], row['xmax'], row['ymax']])
        cropped = frame_bgr[y1:y2, x1:x2]

        if label == 'plat':
            print("[INFO ] Plat terdeteksi.")
            plate = recognize_plate(cropped)
            if plate is not None:
                plate_clean = re.sub(r'[^A-Z0-9]', '', plate.upper())
                print(" [DEBUG ] Plate cleaned:", plate_clean)
                if plate_clean in authorized_plates:
                    print("✅ Plat cocok. Gerbang terbuka.")
                else:
                    print("❌ Plat tidak cocok . Akses ditolak .")
            else:
                print("❌ Gagal membaca plat.")

        elif label == 'orang':
            print("[INFO] Orang terdeteksi.")
            if verify_face(cropped):
                print("✅ Wajah dikenali. Pintu terbuka.")
                cv2.putText(frame_bgr, "Wajah Dikenali", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                print("❌ Wajah tidak dikenali.")
                cv2.putText(frame_bgr, "Wajah Tidak Dikenali", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Gambar bounding box
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 4)

    # Simpan dan tampilkan
    output_path = "/content/output_detected.jpg"
    cv2.imwrite(output_path, frame_bgr)
    print("[INFO] Gambar hasil deteksi disimpan:", output_path)
    display(Image.open(output_path))
    upload_to_firebase(output_path)

# ===[8] UPLOAD KE FIREBASE DENGAN URUTAN ANGKA KE FOLDER GAMBAR===
def upload_to_firebase(file_name):
    counter_file = "/content/image_counter.txt"
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as f:
            counter = int(f.read().strip()) + 1
    else:
        counter = 1

    new_filename = f"{counter}.jpg"
    new_file_path = os.path.join("/content", new_filename)

    cv2.imwrite(new_file_path, cv2.imread(file_name))
    print(f"[INFO] Gambar disimpan dengan nama baru: {new_file_path}")

    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"Gambar/{new_filename}")
        blob.upload_from_filename(new_file_path)
        blob.make_public()
        print("URL file Anda:", blob.public_url)

        metadata = {
            'image_url': blob.public_url,
            'timestamp': time.time(),
            'filename': new_filename
        }

        db_ref = db.reference('uploads').child(new_filename.replace('.', '_'))
        db_ref.set(metadata)
        print("Metadata berhasil diunggah ke Realtime Database.")

        with open(counter_file, 'w') as f:
            f.write(str(counter))

    except Exception as e:
        print("Error uploading file or metadata:", e)

# ===[9] EKSEKUSI===
image_path = "/content/drive/MyDrive/Gambar/IMG_20250310_131825.jpg"
frame = cv2.imread(image_path)
if frame is None:
    raise ValueError("[ERROR ] Gagal membaca gambar !")

print("[INFO ] Gambar berhasil dimuat. Ukuran :", frame.shape)
test_pipeline(frame)
