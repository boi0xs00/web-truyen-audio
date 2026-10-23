import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
import uvicorn

# 1. KHỞI TẠO APP FASTAPI (Phải đặt ở trên cùng)
app = FastAPI()

# 2. MOUNT THƯ MỤC VÀ TEMPLATES
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

def lay_danh_sach_hot():
    stats = doc_thong_ke()
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
    hot_list = []
    for thu_muc_raw, luot_xem in sorted_stats:
        ten_hien_thi = thu_muc_raw.split("#")[0].strip().replace('-', ' ').title()
        anh_bia = None
        cover_path = os.path.join("audio", thu_muc_raw, "cover.jpg")
        if os.path.exists(cover_path):
            anh_bia = f"/audio/{quote(thu_muc_raw)}/cover.jpg"
        hot_list.append({
            "thu_muc_raw": thu_muc_raw,
            "ten_hien_thi": ten_hien_thi,
            "luot_xem": luot_xem,
            "anh_bia": anh_bia
        })
    return hot_list

@app.get("/", response_class=HTMLResponse)
async def trang_chu(request: Request, tag: str = None):
    danh_sach_truyen = []
    danh_sach_tags = set()

    if os.path.exists("audio"):
        for ten in os.listdir("audio"):
            duong_dan = os.path.join("audio", ten)
            if os.path.isdir(duong_dan):
                ten_sach = ten.split("#")[0].strip()
                anh_bia = None
                if os.path.exists(os.path.join(duong_dan, "cover.jpg")):
                    anh_bia = f"/audio/{quote(ten)}/cover.jpg"

                tags = []
                for ten_file in os.listdir(duong_dan):
                    if ten_file.lower() == "tags.txt":
                        try:
                            with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8") as f:
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

    # Đọc identifier của Internet Archive từ file chapters.txt
    archive_identifier = ""
    tong_so_chuong = 0
    chapters_file_path = os.path.join(duong_dan, "chapters.txt")
    if os.path.exists(chapters_file_path):
        try:
            with open(chapters_file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    archive_identifier = lines[0] # Dòng đầu là tên identifier trên Archive (vd: chuong-001)
                    if len(lines) > 1:
                        tong_so_chuong = int(lines[1])
                    else:
                        tong_so_chuong = 1
        except:
            tong_so_chuong = 0

    # Tự động sinh danh sách link audio trỏ trực tiếp tới Internet Archive
    danh_sach_chuong_url = []
    for i in range(1, tong_so_chuong + 1):
        file_name = f"chương-{i:03d}.mp3"
        audio_link = f"https://ia800000.us.archive.org/0/items/{archive_identifier}/{quote(file_name)}"
        danh_sach_chuong_url.append({
            "ten_chuong": f"Chương {i}",
            "link": audio_link
        })

    tags_list = []
    gioi_thieu_noi_dung = "Chưa có phần giới thiệu cho bộ truyện này."
    for ten_file in os.listdir(duong_dan):
        if ten_file.lower() == "tags.txt":
            try:
                with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8") as f:
                    for t in f.read().lower().split("#"):
                        if t.strip(): tags_list.append("#" + t.strip())
            except:
                pass
        elif ten_file.lower() == "intro.txt":
            try:
                with open(os.path.join(duong_dan, ten_file), "r", encoding="utf-8") as f:
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