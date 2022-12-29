1.下載代碼倉庫
```
git clone https://github.com/HHim8826/novel_wenku8.git
cd novel_wenku8
```
2.安裝Python 3.7或更高版本，並使用pip安裝依賴
```
pip install -r requirements.txt
```
3.啟動腳本
```
python get_nov.py
```
4.get_nov.py腳本參數
```
# 下載小說插圖 默認下載
dl_img = True
# 將所有文字內容轉為繁中 默認不轉換
chinese_convert = False
# 將文件容轉為epub 默認不轉換
epub_convert = False
# 下載指定卷 默認不啟用
dl_custom_ch = False
```
