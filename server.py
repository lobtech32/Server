import socket
import struct
import datetime
import time

HOST = '0.0.0.0'
PORT = 8080
YOUR_LOCK_IMEI = '862205059210023' # Kilit IMEI numarası

def generate_l0_command(imei):
    # L0 komutu: Kilidi açma komutu
    # Başlık: 0xFFFF
    # Uzunluk: 0x0008 (8 bayt)
    # Komut Numarası: 0x00L0 (L0 komutu)
    # IMEI: 8 bayt (ASCII'den binary'ye dönüştürülmüş)
    # Checksum: 0x0000 (şimdilik 0, gerçekte hesaplanmalı)
    # Sonu: 0x0000 (Her zaman 0)

    header = b'\xFF\xFF'
    length = struct.pack('>H', 0x0008) # L0 komutunun sabit uzunluğu (örnek)
    command_number = b'\x00\x4C\x30' # 0x00, L, 0 (L0)
    
    # IMEI'yi 8 bayta sığdırmak için padding veya truncating gerekebilir.
    # Örneğimizde string'i direkt bytes'a çeviriyoruz.
    imei_bytes = imei.encode('ascii')[:8].ljust(8, b'\x00') # 8 bayt olmasını sağlar
    
    checksum = b'\x00\x00' # Basitlik için şimdilik 0
    end = b'\x00\x00'

    # Tüm parçaları birleştir
    l0_command = header + length + command_number + imei_bytes + checksum + end
    return l0_command

def handle_connection(conn, addr):
    try:
        print(f"Yeni bağlantı: {addr}")
        
        # İlk 2 baytı başlık olarak oku
        header = conn.recv(2)
        if not header:
            print(f"Bağlantı kapandı: {addr} (Başlık yok)")
            return # Bağlantı kapandığında fonksiyondan çık
        
        # Başlık kontrolü (Omni protokolü 0xFFFF bekler)
        if header != b'\xFF\xFF':
            print(f"Geçersiz başlık alındı (0xFFFF bekleniyordu): {header.hex().upper()}")
            # Geçersiz başlık durumunda da bağlantıyı kapat ve çık
            return

        # Q0 komutu için geri kalan veriyi oku
        # Omni dokümanına göre Q0 komutu: Başlık(2) + Uzunluk(2) + Komut(3) + IMEI(8) + Version(2) + Time(4) + Status(2) + Checksum(2) + End(2) = 27 bytes
        # header'dan sonra 25 bayt daha okunmalı.
        remaining_data = conn.recv(25) # Başlıktan sonraki 25 baytı oku
        if len(remaining_data) < 25:
            print(f"Q0 komutu için eksik veri alındı (beklenen 25, gelen {len(remaining_data)}).")
            return

        command_code_check = remaining_data[2:5] # Command Code (3 bayt)

        if command_code_check == b'\x00\x51\x30': # 0x00Q0
            imei_from_q0 = remaining_data[5:13].decode('ascii').strip('\x00') # IMEI (8 bayt)
            print(f"Kilitten Oturum Açma (Q0) komutu alındı: {imei_from_q0}")

            if imei_from_q0 == YOUR_LOCK_IMEI:
                l0_command = generate_l0_command(YOUR_LOCK_IMEI)
                conn.sendall(l0_command)
                print(f"Kilide açma komutu başarıyla gönderildi.")
            else:
                print(f"Farklı bir IMEI'den Q0 komutu geldi: {imei_from_q0}")
        else:
            print(f"Bilinmeyen komut alındı (Q0 bekleniyordu): {command_code_check.hex().upper()}")

    except ConnectionResetError:
        print(f"Bağlantı istemci tarafından sıfırlandı: {addr}")
    except Exception as e:
        print(f"Bağlantı işlenirken hata oluştu: {e}")
    finally:
        print(f"Bağlantı kapatılıyor: {addr}")
        if conn: # conn nesnesinin var olduğundan emin olun
            conn.close()

# Ana sunucu döngüsü
# Bu dış döngü, sunucunun sürekli olarak çalışmasını sağlar
# ve beklenmedik hatalarda bile yeniden başlatmaya çalışır.
while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(5)
            print(f"Sunucu {HOST}:{PORT} üzerinde dinlemede...")
            print(f"Kilidin {YOUR_LOCK_IMEI} IMEI numarasıyla ayar kurulumu bekleniyor.")

            # Bu iç döngü, soket açık olduğu sürece yeni bağlantıları kabul eder
            while True:
                conn, addr = s.accept()
                handle_connection(conn, addr)

    except OSError as e: # Örneğin, portun zaten kullanımda olması gibi soket hatalarını yakala
        print(f"Soket hatası: {e}. 5 saniye sonra yeniden deniyor...")
        time.sleep(5) # Hata durumunda kısa bir süre bekle
    except Exception as e: # Diğer tüm beklenmedik hataları yakala
        print(f"Genel sunucu hatası: {e}. Sunucu kendini yeniden başlatmaya çalışıyor...")
        time.sleep(5) # Ciddi bir hata durumunda kısa bir süre beklemeden yeniden denemek için
        # Eğer bu hata çok sık tekrar ederse, buraya bir çıkış koşulu eklenebilir.
        # Ancak sürekli dinlemede kalması için yeniden döngüye devam ediyoruz.
