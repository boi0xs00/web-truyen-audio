import os
import re
import json
from urllib.parse import quote
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI()

# Mount thư mục audio local để load ảnh bìa cover, intro, tags nếu có trên máy
if os.path.exists("audio"):
    app.mount("/audio", StaticFiles(directory="audio"), name="audio")

templates = Jinja2Templates(directory="templates")
STAT_FILE = "hot_stats.json"

# ---> ĐƯỜNG DẪN GỐC TERABOX CỦA BẠN (Thay đổi link này nếu cần)
TERABOX_BASE_URL = "https://dm.terabox.com/vietnamese/main?category=all&path=%2Fweb-truyenaudio"

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
    danh_sach = []
    if os.path.exists("audio"):
        for ten_thu_muc in os.listdir("audio"):
            duong_dan_thu_muc = os.path.join("audio", ten_thu_muc)
            if os.path.isdir(duong_dan_thu_muc):
                anh_bia_path = None
                for ten_file in os.listdir(duong_dan_thu_muc):
                    if ten_file.lower().startswith("cover"):
                        anh_bia_path = f"/audio/{quote(ten_thu_muc)}/{quote(ten_file)}"
                        break
                ten_sach = ten_thu_muc.split("#")[0].strip()
                so_luot_xem = stats.get(ten_thu_muc, 0)
                danh_sach.append({
                    "thu_muc": ten_sach,
                    "thu_muc_raw": ten_thu_muc,
                    "ten_hien_thi": ten_sach.replace('-', ' ').title(),
                    "anh_bia": anh_bia_path,
                    "luot_xem": so_luot_xem
                })
    danh_sach.sort(key=lambda x: x["luot_xem"], reverse=True)
    return danh_sach

@app.get("/ghi-nhan/{thu_muc}")
async def ghi_nhan_xem(thu_muc: str):
    stats = doc_thong_ke()
    stats[thu_muc] = stats.get(thu_muc, 0) + 1
    ghi_thong_ke(stats)
    ten_goc = thu_muc.split("#")[0].strip()
    return RedirectResponse(url=f"/nghe/{ten_goc}", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def trang_chu(request: Request):
    danh_sach_truyen = []
    tat_ca_tags = set()
    for t_mac_dinh in ["#hoàn thành", "#đang ra", "#truyện ngắn", "#truyện dài"]:
        tat_ca_tags.add(t_mac_dinh)

    if os.path.exists("audio"):
        for ten_thu_muc in os.listdir("audio"):
            duong_dan_thu_muc = os.path.join("audio", ten_thu_muc)
            if os.path.isdir(duong_dan_thu_muc):
                anh_bia_path = None
                tags_list = []
                for ten_file in os.listdir(duong_dan_thu_muc):
                    if ten_file.lower().startswith("cover"):
                        anh_bia_path = f"/audio/{quote(ten_thu_muc)}/{quote(ten_file)}"
                    elif ten_file.lower() == "tags.txt":
                        try:
                            with open(os.path.join(duong_dan_thu_muc, ten_file), "r", encoding="utf-8") as f:
                                for t in f.read().lower().split("#"):
                                    if t.strip():
                                        tag_chuan = "#" + t.strip()
                                        tags_list.append(tag_chuan)
                                        tat_ca_tags.add(tag_chuan)
                        except:
                            pass
                if "#" in ten_thu_muc:
                    parts = ten_thu_muc.split("#")
                    ten_sach = parts[0].strip()
                    for t in parts[1:]:
                        if t.strip():
                            tag_chuan = "#" + t.strip().lower()
                            tags_list.append(tag_chuan)
                            tat_ca_tags.add(tag_chuan)
                else:
                    ten_sach = ten_thu_muc

                danh_sach_truyen.append({
                    "thu_muc": ten_sach,
                    "thu_muc_raw": ten_thu_muc,
                    "ten_hien_thi": ten_sach.replace('-', ' ').title(),
                    "anh_bia": anh_bia_path,
                    "tags": tags_list,
                    "tags_str": ",".join(tags_list)
                })

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "danh_sach_truyen": danh_sach_truyen,
            "danh_sach_tags": sorted(list(tat_ca_tags)),
            "hot_list": lay_danh_sach_hot()
        }
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

    # Đọc tổng số chương từ file chapters.txt trong thư mục truyện
    tong_so_chuong = 0
    chapters_file_path = os.path.join(duong_dan, "chapters.txt")
    if os.path.exists(chapters_file_path):
        try:
            with open(chapters_file_path, "r", encoding="utf-8") as f:
                tong_so_chuong = int(f.read().strip())
        except:
            tong_so_chuong = 0

    # Tự động sinh danh sách link audio với định dạng chuong-001.mp3, chuong-002.mp3...
    danh_sach_chuong_url = []
    for i in range(1, tong_so_chuong + 1):
        file_name = f"chuong-{i:03d}.mp3"
        audio_link = f"{TERABOX_BASE_URL}/{quote(thu_muc_that)}/{file_name}"
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)