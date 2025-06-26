import socket
import datetime
import struct # 0xFFFF gibi binary değerleri işlemek için

# Kendi sunucu ayarlarınız
HOST = '0.0.0.0'  # Tüm gelen IP adreslerinden bağlantıları dinle (Railway sunucunuzda bu şekilde bırakın)
PORT = 8080       # Kilitlerin bağlanacağı port numarası (Sizin belirttiğiniz port)

# Kilit ve protokol bilgileri (Sizin bilgilerinizle güncellendi!)
YOUR_LOCK_IMEI = '862205059210023' # Kilidinizin gerçek IMEI numarası
OM_MANUFACTURER_CODE = 'OM' # Üretici kodu (protokol belgesinden)
YOUR_USER_ID = 12345 # Kilit açma komutu için kullanacağınız kullanıcı ID'si (Bunu istediğiniz gibi değiştirebilirsiniz)

print("Sunucu başlatılıyor...")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Portu hızlıca yeniden kullanmak için
    s.bind((HOST, PORT))
    s.listen(5) # En fazla 5 bekleyen bağlantıyı kabul et
    print(f"Sunucu {HOST}:{PORT} üzerinde dinlemede...")
    print(f"Kilidin {YOUR_LOCK_IMEI} IMEI numarasıyla bağlantı kurması bekleniyor.")

    while True:
        conn, addr = s.accept() # Bir kilit bağlandığında bağlantıyı kabul et
        with conn:
            print(f"Yeni bağlantı: {addr}")

            try:
                # Kilitlerden gelen veriyi oku
                # Kilitler her zaman 0xFFFF ile başlar, bu yüzden ilk 2 baytı okuyun.
                header = conn.recv(2)
                if not header:
                    print(f"Bağlantı kapandı: {addr}")
                    break

                # 0xFFFF kontrolü yapın
                if header == b'\xff\xff':
                    # Geri kalan veriyi oku (bir satır sonu karakterine kadar)
                    data_buffer = bytearray()
                    while True:
                        byte = conn.recv(1)
                        if not byte or byte == b'\n': # Yeni satır karakterine kadar oku
                            break
                        data_buffer.extend(byte)
                    
                    received_message = data_buffer.decode('utf-8').strip()
                    print(f"Kilitten gelen mesaj: {received_message}")

                    # Oturum Açma (Q0) komutunu kontrol et
                    if received_message.startswith('*Q0'):
                        print(f"Kilitten Oturum Açma (Q0) komutu alındı: {received_message}")

                        # Kilit bağlandığında otomatik olarak L0 (Kilidi Aç) komutu gönder
                        current_time_str = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                        current_timestamp_unix = int(datetime.datetime.now().timestamp())

                        unlock_command_str = (
                            f"*CMDS,{OM_MANUFACTURER_CODE},{YOUR_LOCK_IMEI},"
                            f"{current_time_str},L0,0,{YOUR_USER_ID},{current_timestamp_unix}#\n"
                        )
                        full_unlock_command = struct.pack('>H', 0xFFFF) + unlock_command_str.encode('utf-8')

                        print(f"Kilide gönderilen komut: {unlock_command_str.strip()}")
                        conn.sendall(full_unlock_command)
                        print("Kilide açma komutu başarıyla gönderildi.")

                    else:
                        print(f"Bilinmeyen bir komut alındı: {received_message}")

                else:
                    print(f"Geçersiz başlık alındı (0xFFFF bekleniyordu): {header.hex()}")
                    # Hatalı bir başlık alındığında bu bağlantıyı kapatabilirsiniz
                    break 

            except Exception as e:
                print(f"Bağlantı sırasında hata oluştu: {e}")
            finally:
                print(f"Bağlantı kapatılıyor: {addr}")
                conn.close()

print("Sunucu durduruldu.")
