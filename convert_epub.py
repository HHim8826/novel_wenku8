#-*- coding: utf-8 -*
import json
import os
import random,string
from ebooklib import epub
from concurrent.futures import ProcessPoolExecutor

def get_json(book):
    with open(f'novel/{book}/book_info.json',mode='r',encoding='u8') as f:
        return json.loads(f.read())

def img_list_sort(lis):
    num_list = []
    re_lis = []
    for num in lis:
        num_list.append(num.split('.')[1])
    px = num.split('.')[-1]
    num_list.sort()
    for index_ in range(len(num_list)):
        re_lis.append(str(index_)+'.'+num_list[index_]+'.'+px)
    
    return re_lis

def make_epub(list_,book_json):
    ch_lis = ['nav']
    img_lis = []
    ebook = epub.EpubBook()
    cover_st = False
    for key,val in list_.items():
        if key == '0':
            ebook.set_identifier(book_json['book_identifier'])
            ebook.set_title(book_json['book_title'] + val[0])
            ebook.set_language(book_json['book_language'])
            ebook.add_author(book_json['book_author'])
            ebook.add_metadata('DC', 'description', book_json['description'])
            ebook.add_metadata('DC', 'subject', book_json['tg'])
            ebook.add_metadata(None,'meta','',{'name':'calibre:series','content': book_json['book_title']})
            for file_ in os.listdir(val[1]):
                if file_.startswith('0.') and not file_.endswith('.txt'):
                    with open(val[1]+file_,mode='rb') as f:
                        ebook.set_cover('cover.jpg',f.read())
                        cover_st = True
            if not cover_st:
                with open(book_json['cover'],mode='rb') as f:
                    ebook.set_cover('cover.jpg',f.read())

            
            ch_name = val[0]
            continue
            
        elif val[0] not in {'插图','插圖'}:
            str_ascii = string.ascii_letters + string.digits * 2
            str_ = "".join(random.sample(str_ascii,7))
            ch1 = epub.EpubHtml(title=val[1],file_name=f'{val[1]+str_}.xhtml',lang='zh')
            with open(val[0],mode='r',encoding='utf-8') as f:
                srting = f'<html><body><h1>{val[1]}</h1><p>'
                str_lis = []
                for line in f.readlines():
                    str_lis.append(line)
                    text = "<br>&nbsp;&nbsp;&nbsp;&nbsp;".join(str_lis) + '</p></body></html>'

            nov_text = srting + text
            
            ch1.set_content(nov_text.encode())
            ebook.add_item(ch1)
            
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

        
    ebook.spine = ch_lis
    ebook.add_item(epub.EpubNcx())
    ebook.add_item(epub.EpubNav())
    
    ebook.toc = ('',
        (
            epub.Section('目錄'),
            tuple(ch_lis)
        )
    )
    epub.write_epub(f'novel/{book_json["book_title"]}/{ch_name}.epub', ebook)

def main(book_name):
    book_json = get_json(book_name) 
    with ProcessPoolExecutor(10) as pr:
        for list_ in book_json['title_list']:
            pr.submit(make_epub,list_,book_json)

if __name__ == '__main__':
    book_name = input('請輸入書名: ')
    main(book_name)
