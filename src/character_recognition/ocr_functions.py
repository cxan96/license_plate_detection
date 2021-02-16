import cv2
import numpy as np
import pytesseract
import pandas as pd

###############################################################################

def extract_plate(img, bounding_box):
    x = int(round(bounding_box[0] * img.shape[1]))
    y = int(round(bounding_box[1] * img.shape[0]))
    w = int(round(bounding_box[2] * img.shape[1]))
    h = int(round(bounding_box[3] * img.shape[0]))

    img_bound = img[y : y + h, x : x + w]
    x_start = x
    y_start = y

    return img_bound, x_start, y_start


def extract_plate_hor(img, bounding_box, change, left):
    x = int(round(bounding_box[0] * img.shape[1]))
    y = int(round(bounding_box[1] * img.shape[0]))
    w = int(round(bounding_box[2] * img.shape[1]))
    h = int(round(bounding_box[3] * img.shape[0]))

    if left:
        img_bound = img[y : y + h, x - change : x + w - change]
        x_start = x - change
        y_start = y
    else:
        img_bound = img[y : y + h, x + change : x + w + change]
        x_start = x + change
        y_start = y

    return img_bound, x_start, y_start


def extract_plate_ver(img, bounding_box, change, up):
    x = int(round(bounding_box[0] * img.shape[1]))
    y = int(round(bounding_box[1] * img.shape[0]))
    w = int(round(bounding_box[2] * img.shape[1]))
    h = int(round(bounding_box[3] * img.shape[0]))

    if up:
        img_bound = img[y - change : y + h - change, x : x + w]
        x_start = x
        y_start = y - change
    else:
        img_bound = img[y + change : y + h + change, x : x + w]
        x_start = x
        y_start = y + change

    return img_bound, x_start, y_start


def extract_plate_side(img, bounding_box, change_x, change_y, coords):
    x = int(round(bounding_box[0] * img.shape[1]))
    y = int(round(bounding_box[1] * img.shape[0]))
    w = int(round(bounding_box[2] * img.shape[1]))
    h = int(round(bounding_box[3] * img.shape[0]))

    if coords == 1:  # topright
        img_bound = img[
            y - change_y : y + h - change_y, x + change_x : x + w + change_x
        ]
        x_start = x + change_x
        y_start = y - change_y
    if coords == 2:  # bottomright
        img_bound = img[
            y + change_y : y + h + change_y, x + change_x : x + w + change_x
        ]
        x_start = x + change_x
        y_start = y + change_y
    if coords == 3:  # bottomleft
        img_bound = img[
            y + change_y : y + h + change_y, x - change_x : x + w - change_x
        ]
        x_start = x - change_x
        y_start = y + change_y
    if coords == 4:  # topleft
        img_bound = img[
            y - change_y : y + h - change_y, x - change_x : x + w - change_x
        ]
        x_start = x - change_x
        y_start = y - change_y

    return img_bound, x_start, y_start


def ocr_extraction(img_bound, x_start, y_start):
    gray = cv2.cvtColor(img_bound, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    blur_g = cv2.GaussianBlur(gray, (5, 5), 0)
    blur = cv2.medianBlur(blur_g, 3)
    ret, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    rect_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilation = cv2.dilate(thresh, rect_kern, iterations=1)
    opening = cv2.morphologyEx(dilation, cv2.MORPH_OPEN, rect_kern)

    contours, hierarchy = cv2.findContours(
        opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    sorted_contours = sorted(contours, key=lambda ctr: cv2.boundingRect(ctr)[0])
    
    data_plate = pd.DataFrame()

    for cnt in sorted_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        height, width = gray.shape
        if height / float(h) > 4:
            continue
        ratio = h / float(w)
        if ratio < 1.2:
            continue
        if width / float(w) > 50:
            continue  
        roi = thresh[np.max([y - 5, 0]) : y + h + 5, np.max([x - 5, 0]) : x + w + 5]
        roi = cv2.bitwise_not(roi)
        roi = cv2.medianBlur(roi, 5)
        dat = pytesseract.image_to_data(
            roi,
            config="-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 8 --oem 3",
            output_type="data.frame",
        )
        dat = dat[dat.conf == np.max(dat.conf)]
        dat["x"] = (x / 3) + x_start
        dat["y"] = (y / 3) + y_start
        dat["w"] = w
        dat["h"] = h
        data_plate = pd.concat([data_plate, dat])

    data_plate = data_plate.dropna()
    if not data_plate.empty:
        data_plate = data_plate.drop(
            columns=[
                "level",
                "page_num",
                "block_num",
                "par_num",
                "line_num",
                "word_num",
                "left",
                "top",
                "width",
                "height",
            ]
        )
        
    return data_plate


def ocr(img, bounding_box, method):
    # check which method is used:
    if method == "normal":
        img_bound, x_start, y_start = extract_plate(img, bounding_box)
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "up":
        img_bound, x_start, y_start = extract_plate_ver(
            img, bounding_box, int(bounding_box[1] * img.shape[0] * 0.1), True
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "down":
        img_bound, x_start, y_start = extract_plate_ver(
            img, bounding_box, int(bounding_box[1] * img.shape[0] * 0.1), False
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "left":
        img_bound, x_start, y_start = extract_plate_hor(
            img, bounding_box, int(bounding_box[0] * img.shape[1] * 0.1), True
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "right":
        img_bound, x_start, y_start = extract_plate_hor(
            img, bounding_box, int(bounding_box[0] * img.shape[1] * 0.1), False
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "topright":
        img_bound, x_start, y_start = extract_plate_side(
            img,
            bounding_box,
            int(bounding_box[0] * img.shape[1] * 0.1),
            int(bounding_box[1] * img.shape[0] * 0.1),
            1,
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "bottomright":
        img_bound, x_start, y_start = extract_plate_side(
            img,
            bounding_box,
            int(bounding_box[0] * img.shape[1] * 0.1),
            int(bounding_box[1] * img.shape[0] * 0.1),
            2,
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "bottomleft":
        img_bound, x_start, y_start = extract_plate_side(
            img,
            bounding_box,
            int(bounding_box[0] * img.shape[1] * 0.1),
            int(bounding_box[1] * img.shape[0] * 0.1),
            3,
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    if method == "topleft":
        img_bound, x_start, y_start = extract_plate_side(
            img,
            bounding_box,
            int(bounding_box[0] * img.shape[1] * 0.1),
            int(bounding_box[1] * img.shape[0] * 0.1),
            4,
        )
        data_plate = ocr_extraction(
            img_bound, x_start, y_start
        )

    return data_plate


def ocr_validation(data_plate):
    data_plate = data_plate.reset_index()
    
    final_frame = pd.DataFrame()
    
    for i in range(len(data_plate)):
        if i not in data_plate.index: 
            continue
        
        curr_frame = data_plate[(data_plate["x"] <= data_plate.x[i] + 1) & 
                                (data_plate["x"] >= data_plate.x[i] - 1) & 
                                (data_plate["y"] <= data_plate.y[i] + 1) &
                                (data_plate["y"] >= data_plate.y[i] - 1)]
        data_plate.drop(curr_frame.index, inplace=True)
        
        best_conf = curr_frame[curr_frame["conf"] == np.max(curr_frame["conf"])]
        if len(best_conf) > 1: best_conf = best_conf.head(1)
        final_frame = pd.concat([final_frame, best_conf])
    
    if not final_frame.empty:
        final_frame = final_frame[final_frame["conf"] >= 40] 
        final_frame = final_frame.sort_values(by=["x"])   
        final_frame.astype({"text": "string"}).dtypes
            
        plate = ""
        for char in final_frame.text:
            if isinstance(char, str): 
                plate += char
            else: 
                plate += str(int(char))
        
        return plate
    else:
        return ""
    
    
###############################################################################    

if __name__ == "__main__":
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    img = cv2.imread(str(data_dir / "validation_eu" / "RK101AO_car_eu.jpg"))
    bounding_box = (305 / 608, 267 / 456, (416 - 305) / 608, (292 - 267) / 456)
   
    methods = [
        "normal",
        "up",
        "down",
        "left",
        "right",
        "topright",
        "bottomright",
        "bottomleft",
        "topleft",
    ]
    
    confi_frame = pd.DataFrame()

    for m in methods:
        data_plate = ocr(img, bounding_box, m)
        confi_frame = pd.concat([confi_frame, data_plate])

    char = ocr_validation(confi_frame)

    print(char)