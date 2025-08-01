# code_scraper_test.py (Versi 3.5 - Penanganan Hasil Tunggal & Logika Status Final)

import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def print_banner():
    print("="*70)
    print("\nSewu Scrap - Google Maps Scraper v3.5 (Robust Build)")
    print("="*70)
    print("PERINGATAN: Gunakan secara bijak untuk riset internal & non-komersial.")

def setup_driver(headless=True):
    print("[SETUP] Menginisialisasi driver Chrome...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=id-ID")
    if headless:
        options.add_argument("--headless")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def main(search_query=None, output_filename=None, headless_mode_enabled=True):
    """
    Fungsi utama untuk menjalankan proses scraping Google Maps.
    """
    RESTART_INTERVAL = 50

    print_banner()
    if search_query is None:
        search_query = input("Masukkan kata kunci pencarian: ").strip()
    if output_filename is None:
        output_filename = input("Nama file output CSV [hasil_scrape.csv]: ").strip() or "hasil_scrape.csv"

    driver = setup_driver(headless=headless_mode_enabled)
    scraped_data = []
    
    try:
        search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        driver.get(search_url)
        wait = WebDriverWait(driver, 20)

        try:
            print("[INFO] Mencari pop-up persetujuan cookie...")
            consent_button_selector = 'button[aria-label*="Accept all"], button[aria-label*="Setuju semua"]'
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, consent_button_selector))).click()
            print("[INFO] Pop-up persetujuan diklik.")
        except TimeoutException:
            print("[INFO] Tidak ada pop-up persetujuan yang ditemukan.")

        unique_urls = []
        
        print("[INFO] Mendeteksi tipe halaman hasil pencarian...")
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]')))
            print("[INFO] Halaman 'Daftar Hasil' terdeteksi. Memulai proses scroll...")
            
            RESULTS_SELECTOR = 'a.hfpxzc'
            patience_counter, patience_threshold, last_known_count = 0, 3, 0
            
            while patience_counter < patience_threshold:
                try:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]'))
                    time.sleep(3)
                    current_card_count = len(driver.find_elements(By.CSS_SELECTOR, RESULTS_SELECTOR))
                    if current_card_count > last_known_count:
                        last_known_count = current_card_count
                        patience_counter = 0
                        print(f"  -> Menemukan {last_known_count} URL... (Kesabaran direset)")
                    else:
                        patience_counter += 1
                        print(f"  -> Jumlah URL tidak bertambah. (Kesabaran: {patience_counter}/{patience_threshold})")
                except Exception as e:
                    print(f"[ERROR] Error saat scroll: {e}, menghentikan scroll.")
                    break
            
            place_links = driver.find_elements(By.CSS_SELECTOR, RESULTS_SELECTOR)
            urls = [link.get_attribute('href') for link in place_links if link.get_attribute('href')]
            unique_urls = list(dict.fromkeys(urls))
            print(f"[INFO] Scroll selesai. Ditemukan {len(unique_urls)} URL unik.")

        except TimeoutException:
            print("[INFO] Halaman 'Detail Langsung' terdeteksi.")
            unique_urls = [driver.current_url]

        # === LANGKAH 2: KUNJUNGI SETIAP URL UNTUK EKSTRAKSI DETAIL ===
        print(f"[INFO] Memulai ekstraksi detail dari {len(unique_urls)} URL...")
        for i, url in enumerate(unique_urls):
            # [PERUBAHAN] Logika restart driver menggunakan nilai dari argumen
            if i > 0 and i % RESTART_INTERVAL == 0:
                print(f"\n[STABILITAS] Mencapai batas {RESTART_INTERVAL} URL. Merestart driver...")
                driver.quit()
                driver = setup_driver(headless=headless_mode_enabled)
                wait = WebDriverWait(driver, 20)
                print("[STABILITAS] Driver berhasil direstart. Melanjutkan proses...\n")
            
            try:
                if driver.current_url != url:
                    driver.get(url)

                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
                time.sleep(1.5)

                nama = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text
                
                rating, ulasan = "N/A", 0
                try:
                    rating_text = driver.find_element(By.CSS_SELECTOR, 'div.F7nice').text.strip()
                    parts = rating_text.split('(')
                    rating = parts[0].strip()
                    if len(parts) > 1:
                        ulasan_match = re.search(r'(\d[\d,.]*)', parts[1])
                        if ulasan_match: ulasan = int(re.sub(r'[.,]', '', ulasan_match.group(1)))
                except NoSuchElementException: pass

                status_operasional = "Tidak Tutup Permanen"
                try:
                    driver.find_element(By.CSS_SELECTOR, 'span.fCEvvc')
                    status_operasional = "Tutup Permanen"
                except NoSuchElementException:
                    pass

                alamat, website, telepon = "N/A", "N/A", "N/A"
                try:
                    address_element = driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]')
                    alamat = address_element.find_element(By.CSS_SELECTOR, 'div.Io6YTe').text
                except NoSuchElementException: pass
                try:
                    website_element = driver.find_element(By.CSS_SELECTOR, '[data-item-id="authority"]')
                    website = website_element.find_element(By.CSS_SELECTOR, 'div.Io6YTe').text
                except NoSuchElementException: pass
                try:
                    phone_element = driver.find_element(By.CSS_SELECTOR, '[data-item-id*="phone:tel:"]')
                    telepon = phone_element.find_element(By.CSS_SELECTOR, 'div.Io6YTe').text
                except NoSuchElementException: pass

                current_url = driver.current_url
                lat, lon = "N/A", "N/A"
                if "@" in current_url:
                    try:
                        coords_part = current_url.split('@')[1]
                        coords_array = coords_part.split(',')
                        lat, lon = coords_array[0], coords_array[1]
                    except (IndexError, Exception): pass
                else:
                    match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', current_url)
                    if match:
                        lat, lon = match.group(1), match.group(2)

                data = {
                    "Nama Tempat": nama,
                    "Status Operasional": status_operasional,
                    "Rating": rating,
                    "Jumlah Ulasan": ulasan,
                    "Alamat": alamat,
                    "Situs Web": website,
                    "Nomor Telepon": telepon,
                    "URL Google Maps": current_url,
                    "Latitude": lat,
                    "Longitude": lon,
                }
                scraped_data.append(data)
                print(f"  [OK] {i + 1}/{len(unique_urls)} - {nama} | Status: {status_operasional}")

            except TimeoutException:
                print(f"  [GAGAL] {i + 1}/{len(unique_urls)} - Timeout saat memuat URL: {url}")
            except Exception as e:
                print(f"  [ERROR] {i + 1}/{len(unique_urls)} - Terjadi error pada URL {url}: {e}")
    
    finally:
        driver.quit()

    if scraped_data:
        print(f"\n[INFO] Berhasil mengekstrak {len(scraped_data)} data. Menyimpan ke {output_filename}...")
        df = pd.DataFrame(scraped_data)
        df = df.drop_duplicates(subset=["Nama Tempat", "Alamat"])
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print("==============================================")
        print("  ✅ PROYEK SELESAI DAN BERHASIL! ✅")
        print("==============================================")
    else:
        print("[INFO] Tidak ada data yang berhasil diekstrak.")

if __name__ == '__main__':
    main()