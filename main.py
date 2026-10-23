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
                        tong_so_chuong = 1 # Mặc định tạm thời nếu chỉ có dòng identifier
        except:
            tong_so_chuong = 0

    # Tự động sinh danh sách link audio trỏ trực tiếp tới Internet Archive
    danh_sach_chuong_url = []
    for i in range(1, tong_so_chuong + 1):
        file_name = f"chương-{i:03d}.mp3"
        # Cấu trúc Direct Link của Internet Archive
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