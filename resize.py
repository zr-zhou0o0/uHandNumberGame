
import cv2

img_path = "4b31af7fd7792e4dd775042dcad500a.jpg"

img = cv2.imread(img_path)
resized_img = cv2.resize(img, (64, 64))

cv2.imwrite("resized_" + img_path, resized_img)