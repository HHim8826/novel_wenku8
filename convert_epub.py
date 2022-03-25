#-*- coding: utf-8 -*
import json
import os
from ebooklib import epub
from concurrent.futures import ProcessPoolExecutor

def get_json(book):
    with open(f'novel/{book}/book_info.json',mode='r',encoding='u8') as f:
        return json.loads(f.read())

book_name = '小书痴的下克上～为了成为图书管理员不择手段～'
book_json = get_json(book_name)

def img_list_sort(lis):
    num_list = []
    re_lis = []
    for num in lis:
        num_list.append(num.split('.')[1])
    fex = num.split('.')[-1]
    num_list.sort()
    for index_ in range(len(num_list)):
        re_lis.append(str(index_)+'.'+num_list[index_]+'.'+fex)
    
    return re_lis
        

def make_epub(list_):
    ch_lis = []
    img_lis = []
    ebook = epub.EpubBook()
    for key,val in list_.items():
        if key == '0':
            ebook.set_identifier(book_json['book_identifier'])
            ebook.set_title(book_json['book_title'] + val)
            ebook.set_language(book_json['book_language'])
            ebook.add_author(book_json['book_author'])
            ebook.add_metadata('DC', 'description', book_json['description'])
            with open(book_json['cover'],mode='rb') as f:
                ebook.set_cover('cover.jpg',f.read())
            
            ch_name = val
            continue
        elif val[0] != '插图':
            if key == '1':
                fr_name = val[1]
            
            ch1 = epub.EpubHtml(title=val[1],file_name=f'{val[1]}.xhtml',lang='zh')
            with open(val[0],mode='r',encoding='utf-8') as f:
                srting = f'<html><body><h1>{val[1]}</h1><p>'
                str_lis = []
                for line in f.readlines():
                    str_lis.append(line)
                    text = "<p>".join(str_lis) + '</p></body></html>'
            
            nov_text = srting + text
                    
            ch1.set_content(nov_text.encode())
            ebook.add_item(ch1)
            
            ch_lis.insert(0,'nav')
            ebook.spine = ch_lis
            
            ebook.add_item(epub.EpubNcx())
            ebook.add_item(epub.EpubNav())

            ch_lis.append(ch1)
        else:
            for file_ in os.listdir(val[1]):
                if not file_.endswith('txt'):
                    img_lis.append(file_)
            img_lis = img_list_sort(img_lis)

            for file_ in img_lis:    
                img_ch = epub.EpubImage()
                with open(val[1]+file_,mode='rb') as f:
                    img_ch.file_name = file_
                    img_ch.media_type = 'image/jpeg'
                    img_ch.content = f.read()
                    ebook.add_item(img_ch)            
                    ch_img = epub.EpubHtml(title=f'{file_}', file_name=f'{file_}.xhtml', lang='zh')
                    ch_img.content = f'<img alt="image/jpeg" src="{file_}"/>'
                    ebook.add_item(ch_img)
                    ch_lis.append(ch_img)
                    ebook.spine = ch_lis
        
        ebook.toc = (epub.Link(f'{fr_name}.xhtml', ch_name, ch_name),
            (
                epub.Section('目錄'),
                tuple(ch_lis)
            )
        )
        epub.write_epub(f'novel/{book_name}/{ch_name}.epub', ebook)

if __name__ == '__main__':
    with ProcessPoolExecutor(10) as pr:
        for list_ in book_json['title_list']:
            pr.submit(make_epub,list_)

