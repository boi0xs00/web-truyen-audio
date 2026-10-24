import os
import json
import urllib.request
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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
        except:
            return {}
    return {}

def ghi_thong_ke(data):
    with open(STAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Hàm tìm file ảnh bìa hỗ trợ nhiều định dạng (.jpg, .jpeg, .png, .webp)
def tim_anh_bia(duong_dan_thu_muc, thu_muc_raw):
    cac_dinh_dang = ["cover.jpg", "cover.jpeg", "cover.png", "cover.webp", "Cover.jpg", "Cover.png"]
    for ten_file in cac_dinh_dang:
        if os.path.exists(os.path.join(duong_dan_thu_muc, ten_file)):
            return f"/audio/{quote(thu_muc_raw)}/{ten_file}"
    return None

def lay_danh_sach_hot():
    stats = doc_thong_ke()
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
    hot_list = []
    for thu_muc_raw, luot_xem in sorted_stats:
        ten_hien_thi = thu_muc_raw.split("#")[0].strip().replace('-', ' ').title()
        duong_dan_thu_muc = os.path.join("audio", thu_muc_raw)
        anh_bia = tim_anh_bia(duong_dan_thu_muc, thu_muc_raw)

        hot_list.append({
            "thu_muc_raw": thu_muc_raw,
            "ten_hien_thi": ten_hien_thi,
            "luot_xem": luot_xem,
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
        except:
            pass

    return raw_text

@app.get("/", response_class=HTMLResponse)
async def trang_chu(request: Request, tag: str = None):
    danh_sach_truyen = []
    danh_sach_tags = set()

    if os.path.exists("audio"):
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
                                    if t.strip(): tags.append("#" + t.strip().lower())
                        except:
                            pass

                if "#" in ten:
                    for t in ten.split("#")[1:]:
                        if t.strip(): tags.append("#" + t.strip().lower())

                if not tags: tags = ["#sắc hiệp", "#audio"]

                for t in tags: danh_sach_tags.add(t)

                danh_sach_truyen.append({
                    "thu_muc_raw": ten,
                    "ten_hien_thi": ten_sach.replace('-', ' ').title(),
                    "anh_bia": anh_bia,
                    "tags": tags,
                    "tags_str": " ".join(tags)
                })

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
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/nghe/{quote(thu_muc_raw)}", status_code=303)

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
        except:
            pass

    archive_identifier = lay_archive_identifier(raw_content, ten_sach)

    danh_sach_chuong_url = []
    try:
        api_url = f"https://archive.org/metadata/{archive_identifier}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            files = data.get('files', [])

            mp3_files = [f['name'] for f in files if f.get('name', '').lower().endswith('.mp3')]
            mp3_files = sorted(mp3_files)

            for file_name in mp3_files:
                ten_hien_thi = file_name.replace('.mp3', '').replace('-', ' ').title()
                audio_link = f"https://archive.org/download/{archive_identifier}/{quote(file_name)}"
                danh_sach_chuong_url.append({
                    "ten_chuong": ten_hien_thi,
                    "link": audio_link
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
                        if t.strip(): tags_list.append("#" + t.strip())
            except:
                pass
        elif ten_file.lower() == "intro.txt":
            try:
                with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8-sig") as f:
                    gioi_thieu_noi_dung = f.read()
            except:
                pass

    if "#" in thu_muc_that:
        for t in thu_muc_that.split("#")[1:]:
            if t.strip(): tags_list.append("#" + t.strip().lower())
    if not tags_list: tags_list = ["#sắc hiệp", "#audio"]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ten_truyen": ten_sach.replace('-', ' ').title(),
            "thu_muc": quote(thu_muc_that),
            "danh_sach_chuong": danh_sach_chuong_url,
            "story_tags": sorted(list(set(tags_list))),
            "hot_list": lay_danh_sach_hot(),
            "gioi_thieu": gioi_thieu_noi_dung
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)