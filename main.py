import os
import json
import random
import unicodedata
import urllib.request
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import quote, urlparse
import uvicorn

app = FastAPI()

if os.path.exists("audio"):
    app.mount("/audio", StaticFiles(directory="audio"), name="audio")

templates = Jinja2Templates(directory="templates")
STAT_FILE = "hot_stats.json"


def doc_thong_ke():
    if os.path.exists(STAT_FILE):
        try:
            with open(STAT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def ghi_thong_ke(data):
    with open(STAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def tim_anh_bia(duong_dan_thu_muc, thu_muc_raw):
    """Tìm ảnh bìa chính xác, nếu thư mục đổi tên sẽ quét fallback theo tên gốc"""
    cac_dinh_dang = [
        "cover.jpg", "cover.jpeg", "cover.png", "cover.webp",
        "Cover.jpg", "Cover.jpeg", "Cover.png", "Cover.webp"
    ]
    if os.path.exists(duong_dan_thu_muc):
        for ten_file in cac_dinh_dang:
            if os.path.exists(os.path.join(duong_dan_thu_muc, ten_file)):
                return f"/audio/{quote(thu_muc_raw)}/{ten_file}"

    if os.path.exists("audio"):
        ten_chuan = thu_muc_raw.split("#")[0].strip().lower()
        for folder_name in os.listdir("audio"):
            folder_clean = folder_name.split("#")[0].strip().lower()
            if folder_clean == ten_chuan:
                real_dir = os.path.join("audio", folder_name)
                for ten_file in cac_dinh_dang:
                    if os.path.exists(os.path.join(real_dir, ten_file)):
                        return f"/audio/{quote(folder_name)}/{ten_file}"
    return None


def lay_danh_sach_hot():
    stats = doc_thong_ke()
    if not os.path.exists("audio"):
        return []

    existing_folders = [f for f in os.listdir("audio") if os.path.isdir(os.path.join("audio", f))]

    aggregated_stats = {}
    cleaned_stats = {}
    for folder_key, views in stats.items():
        matched_real_folder = None
        if folder_key in existing_folders:
            matched_real_folder = folder_key
        else:
            base_key = folder_key.split("#")[0].strip().lower()
            for ef in existing_folders:
                if ef.split("#")[0].strip().lower() == base_key:
                    matched_real_folder = ef
                    break

        if matched_real_folder:
            cleaned_stats[folder_key] = views
            base_name = matched_real_folder.split("#")[0].strip().lower()
            if base_name not in aggregated_stats:
                aggregated_stats[base_name] = {
                    "views": 0,
                    "thu_muc_raw": matched_real_folder
                }
            aggregated_stats[base_name]["views"] += views

    if len(cleaned_stats) != len(stats):
        ghi_thong_ke(cleaned_stats)

    sorted_items = sorted(aggregated_stats.values(), key=lambda x: x["views"], reverse=True)[:5]

    hot_list = []
    for item in sorted_items:
        thu_muc_raw = item["thu_muc_raw"]
        ten_hien_thi = thu_muc_raw.split("#")[0].strip().replace('-', ' ').title()
        duong_dan_thu_muc = os.path.join("audio", thu_muc_raw)
        anh_bia = tim_anh_bia(duong_dan_thu_muc, thu_muc_raw)

        hot_list.append({
            "thu_muc_raw": thu_muc_raw,
            "ten_hien_thi": ten_hien_thi,
            "luot_xem": item["views"],
            "anh_bia": anh_bia
        })
    return hot_list


def lay_archive_identifier(raw_text, ten_sach_mac_dinh):
    raw_text = raw_text.strip()
    if not raw_text:
        return ten_sach_mac_dinh.lower().replace(' ', '-')
    if "archive.org" in raw_text:
        try:
            path = urlparse(raw_text).path
            parts = [p for p in path.split('/') if p]
            if "details" in parts or "download" in parts or "items" in parts:
                idx = max(parts.index("details") if "details" in parts else -1,
                          parts.index("download") if "download" in parts else -1,
                          parts.index("items") if "items" in parts else -1)
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except Exception:
            pass
    return raw_text


def lay_tat_ca_truyen():
    danh_sach = []
    if not os.path.exists("audio"):
        return danh_sach

    for ten in os.listdir("audio"):
        duong_dan = os.path.join("audio", ten)
        if os.path.isdir(duong_dan):
            ten_sach = ten.split("#")[0].strip()
            anh_bia = tim_anh_bia(duong_dan, ten)
            tags = []
            for ten_file in os.listdir(duong_dan):
                if ten_file.lower() == "tags.txt":
                    try:
                        with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8-sig") as f:
                            for t in f.read().split("#"):
                                if t.strip():
                                    tags.append("#" + t.strip().lower())
                    except Exception:
                        pass
            if "#" in ten:
                for t in ten.split("#")[1:]:
                    if t.strip():
                        tags.append("#" + t.strip().lower())
            if not tags:
                tags = ["#sắc hiệp", "#audio"]
            danh_sach.append({
                "thu_muc_raw": ten,
                "ten_hien_thi": ten_sach.replace('-', ' ').title(),
                "anh_bia": anh_bia,
                "tags": list(set(tags)),
                "tags_str": " ".join(tags)
            })
    return danh_sach


@app.get("/", response_class=HTMLResponse)
async def trang_chu(request: Request, tag: str = None):
    danh_sach_truyen = lay_tat_ca_truyen()
    danh_sach_tags = set()
    for tr in danh_sach_truyen:
        for t in tr["tags"]:
            danh_sach_tags.add(t)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "danh_sach_truyen": danh_sach_truyen,
            "danh_sach_tags": sorted(list(danh_sach_tags)),
            "hot_list": lay_danh_sach_hot()
        }
    )


@app.get("/ghi-nhan/{thu_muc_raw}", response_class=HTMLResponse)
async def ghi_nhan_luot_xem(thu_muc_raw: str):
    stats = doc_thong_ke()
    stats[thu_muc_raw] = stats.get(thu_muc_raw, 0) + 1
    ghi_thong_ke(stats)
    return RedirectResponse(url=f"/nghe/{quote(thu_muc_raw)}", status_code=303)


@app.get("/api/archive-text/{identifier}/{filename:path}", response_class=PlainTextResponse)
async def lay_noi_dung_text_archive(identifier: str, filename: str):
    """Proxy tải nội dung file .txt từ Internet Archive và chuẩn hóa Unicode NFC"""
    url = f"https://archive.org/download/{quote(identifier)}/{quote(filename)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_bytes = response.read()
            try:
                text = raw_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw_bytes.decode('utf-8', errors='replace')

            # Gộp dấu tổ hợp (NFD) thành dựng sẵn (NFC) để tránh tách rời dấu thanh
            text = unicodedata.normalize('NFC', text)

            return PlainTextResponse(content=text)
    except Exception as e:
        return PlainTextResponse(
            content=f"Không thể tải nội dung văn bản từ Archive.org.\nChi tiết lỗi: {e}",
            status_code=500
        )


@app.get("/nghe/{ten_truyen_url}", response_class=HTMLResponse)
async def nghe_truyen(request: Request, ten_truyen_url: str):
    thu_muc_that = None
    if os.path.exists("audio"):
        for ten in os.listdir("audio"):
            if os.path.isdir(os.path.join("audio", ten)):
                ten_goc = ten.split("#")[0].strip()
                if ten == ten_truyen_url or ten_goc.lower() == ten_truyen_url.strip().lower():
                    thu_muc_that = ten
                    break
    if not thu_muc_that:
        return HTMLResponse("Không tìm thấy thư mục truyện!", status_code=404)

    duong_dan = os.path.join("audio", thu_muc_that)
    ten_sach = thu_muc_that.split("#")[0].strip()
    raw_content = ""
    chapters_file_path = os.path.join(duong_dan, "chapters.txt")
    if os.path.exists(chapters_file_path):
        try:
            with open(chapters_file_path, "r", encoding="utf-8-sig") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    raw_content = lines[0]
        except Exception:
            pass

    archive_identifier = lay_archive_identifier(raw_content, ten_sach)
    danh_sach_chuong_url = []
    danh_sach_text_url = []

    try:
        api_url = f"https://archive.org/metadata/{archive_identifier}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            files = data.get('files', [])

            mp3_files = sorted([f['name'] for f in files if f.get('name', '').lower().endswith('.mp3')])
            for file_name in mp3_files:
                ten_hien_thi = file_name.replace('.mp3', '').replace('-', ' ').title()
                audio_link = f"https://archive.org/download/{archive_identifier}/{quote(file_name)}"
                danh_sach_chuong_url.append({
                    "ten_chuong": ten_hien_thi,
                    "link": audio_link
                })

            txt_files = sorted([
                f['name'] for f in files
                if f.get('name', '').lower().endswith('.txt')
                and not f.get('name', '').lower().endswith('_djvu.txt')
            ])
            for file_name in txt_files:
                ten_hien_thi = file_name.replace('.txt', '').replace('-', ' ').title()
                download_link = f"https://archive.org/download/{archive_identifier}/{quote(file_name)}"
                danh_sach_text_url.append({
                    "ten_file": ten_hien_thi,
                    "file_goc": file_name,
                    "download_link": download_link
                })
    except Exception as e:
        print(f"Lỗi lấy dữ liệu Archive cho truyện {archive_identifier}:", e)

    if not danh_sach_chuong_url:
        danh_sach_chuong_url.append({
            "ten_chuong": "Chương 1",
            "link": f"https://archive.org/download/{archive_identifier}/chuong-001.mp3"
        })

    tags_list = []
    gioi_thieu_noi_dung = "Chưa có phần giới thiệu cho bộ truyện này."
    for ten_file in os.listdir(duong_dan):
        if ten_file.lower() == "tags.txt":
            try:
                with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8-sig") as f:
                    for t in f.read().lower().split("#"):
                        if t.strip():
                            tags_list.append("#" + t.strip())
            except Exception:
                pass
        elif ten_file.lower() == "intro.txt":
            try:
                with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8-sig") as f:
                    gioi_thieu_noi_dung = f.read()
            except Exception:
                pass

    if "#" in thu_muc_that:
        for t in thu_muc_that.split("#")[1:]:
            if t.strip():
                tags_list.append("#" + t.strip().lower())

    if not tags_list:
        tags_list = ["#sắc hiệp", "#audio"]

    current_tags_set = set(tags_list)

    tat_ca = lay_tat_ca_truyen()
    truyen_lien_quan = []
    for tr in tat_ca:
        if tr["thu_muc_raw"] != thu_muc_that:
            if set(tr["tags"]) & current_tags_set:
                truyen_lien_quan.append(tr)

    if len(truyen_lien_quan) > 6:
        truyen_lien_quan = random.sample(truyen_lien_quan, 6)
    else:
        random.shuffle(truyen_lien_quan)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ten_truyen": ten_sach.replace('-', ' ').title(),
            "thu_muc": thu_muc_that,
            "archive_id": archive_identifier,
            "anh_bia": tim_anh_bia(duong_dan, thu_muc_that),
            "danh_sach_chuong": danh_sach_chuong_url,
            "danh_sach_text": danh_sach_text_url,
            "story_tags": sorted(list(current_tags_set)),
            "hot_list": lay_danh_sach_hot(),
            "gioi_thieu": gioi_thieu_noi_dung,
            "truyen_lien_quan": truyen_lien_quan
        }
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)