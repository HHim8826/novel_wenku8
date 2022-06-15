#-*- coding: utf-8 -*-
import json
import requests
import asyncio
import re
import aiofiles
import aiohttp
import zhconv
import os
import convert_epub
from tqdm import tqdm

# 下載小說插圖 默認下載
dl_img = True
# 將所有文字內容轉為繁中 默認不轉換
chinese_convert = False
# 將文件容轉為epub 默認不轉換
epub_convert = False
book_title_lis = []
book_info = {}

def convert2chinese(text):
    return zhconv.convert(text,'zh-hk')

def get_htm(url):
    req = requests.get(url)
    req.encoding = 'gbk'
    text = req.text

    if chinese_convert:
        text = convert2chinese(text)
    
    all_novel_name = re.search(r'<div id="title">(?P<name>.*?)</div>',text,re.S) 
    find_author = re.search(r'<div id="info">作者：(?P<author>.*?)</div>',text,re.S) 
    nov_name = all_novel_name.group('name')
    author_name = find_author.group('author')

    book_info['book_title'] = nov_name
    book_info['book_author'] = author_name
    book_info['book_language'] = 'zh'
    book_info['book_identifier'] = url

    return text,nov_name

def get_more_info(nov_id,novel_name,img_url,headers):
    try:
        os.makedirs(f'novel/{novel_name}')
    except FileExistsError:
        pass

    req_img = requests.get(img_url,headers=headers)
    with open(f'novel/{novel_name}/{img_url.split("/")[-1]}',mode='wb') as f:
        f.write(req_img.content)
        book_info['cover'] = f'novel/{novel_name}/{img_url.split("/")[-1]}'
    
    url = f'http://www.wenku8.net/book/{nov_id}.htm'
    req = requests.get(url)
    req.encoding = 'gbk'
    text = req.text
    if chinese_convert:
        text = convert2chinese(text)

    dc_compile = re.compile(r'\<span\sclass\=\"hottext\"\>(內容簡介|内容简介)\：\<\/span><br \/\>\<span\sstyle\=\"font-size\:\d+px\;\"\>(?P<dc>.*?)\<\/span\>',re.S)
    tg_compile = re.compile(r'\<span\sclass\=\"hottext\"\sstyle\=\"font\-size\:\d+px\;\"\>\<b\>作品Tags：(?P<tg>.*?)\<\/b\>\<\/span\>\<br \/>')
    res_dc = dc_compile.search(text)
    res_tg = tg_compile.search(text)

    dc_info = res_dc.group('dc')
    dc_info = dc_info.replace('\r\n','')
    book_info['description'] = dc_info

    tg_info = res_tg.group('tg')
    book_info['tg'] = tg_info

def get_novel_title(html):
    ch_lis = []

    chapter_compile = re.compile(r'\<td\sclass\=\"vcss\"\scolspan\=\"\w+\"\svid=\"(?P<ch_id>\w+?)\"\>(?P<novel_name>.*?)\<\/td\>',re.S)
    res_chapter = chapter_compile.finditer(html)
    
    for itr in res_chapter:
        ch_id = itr.group('ch_id')
        novel_name = itr.group('novel_name')
        ch_lis.append([ch_id,novel_name])

    return ch_lis

def make_dir(file,novel_name):
    try:
        os.makedirs(f'novel/{novel_name}/{file}')
    except FileExistsError:
        pass
        
def name_replace(replace_str:str):
    replace_list = [b'\\',b"/",b":",b"*",b"?",b'"',b"<",b">",b"|"]
    replace_str = replace_str.strip()
    replace_str = replace_str.encode()
    for str in replace_list:
        replace_str = replace_str.replace(str,b'')
    replace_str = replace_str.decode('u8')
    return replace_str

def get_novel_text(text):
    obj = re.compile(r'&nbsp;&nbsp;&nbsp;&nbsp;(?P<text_re>.*?)\n',re.S)
    
    text_line = obj.finditer(text)
    text_list = []

    for it in text_line:
        if '<br />' in it.group('text_re'):
            line = it.group('text_re')[:-7]
        elif it.group('text_re') == '\r':
            continue
        else:
            line = it.group('text_re')
        
        text_list.append(line)
    
    text_list[-1] = text_list[-1].replace('<span></span></div>','')
    return text_list

async def get_img(url,file,all_novel_name,session,r):
    async with session.get(url) as req:
        async with aiofiles.open(f'novel/{all_novel_name}/{file}/{r}.{url.split("/")[-1]}',mode='wb') as aiofile:
            await aiofile.write(await req.content.read())

async def pack_dl(pack_url,session,ch_name,all_novel_name,pbar):
    title_dict = {}
    
    make_dir(ch_name,all_novel_name)
    async with session.get(pack_url) as req:
        pack_content = await req.text()
        text_list = pack_content.split('<div class="chaptertitle">')
        
        r = 0
        count_ = 0
        
        title_dict[count_] = [ch_name,f"novel/{all_novel_name}/{ch_name}/"]
        count_ += 1
        
        for text in text_list:
            title_ = re.findall(r'\<a\sname\=\"\w+\"\>(.*?)\<\/a\>',text)
            try:
                if '插图' in title_[0] or '插圖' in title_[0]:
                    r1 = 0
                    img_re = re.finditer(r'\<\/div\>\<div\sclass\=\"divimage\"\sid=\"\w+?\.jpg\"\stitle\=\"(?P<url>.*?)\"\>',text)
                    for itr in img_re:
                        img_url = itr.group('url')
                        await get_img(img_url,ch_name,all_novel_name,session,r1)
                        r1 += 1
                    title_dict[count_] = [title_[0].split(' ')[-1],f"novel/{all_novel_name}/{ch_name}/"]
                    count_ += 1
                    continue

                async with aiofiles.open(f'novel/{all_novel_name}/{ch_name}/{r}.{name_replace(title_[0].split(" ")[-1])}.txt',mode='w',encoding='utf-8') as aiofile:
                    title_dict[count_] = [f"novel/{all_novel_name}/{ch_name}/{r}.{name_replace(title_[0].split(' ')[-1])}.txt",name_replace(title_[0].split(' ')[-1])]
                    
                    text_lis = get_novel_text(text)
                    novel_text = '\n\n'.join(text_lis)
                    if chinese_convert:
                        novel_text = convert2chinese(novel_text)
                    await aiofile.write(novel_text)
                    r += 1
                    count_ += 1
            except:
                continue
    
    book_title_lis.append(title_dict)
    pbar.update(1)

async def main(novel_id):
    tasks = []
    headers = {'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
    try:
        version = 2
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        img_url = f'https://img.wenku8.com/image/{version}/{novel_id}/{novel_id}s.jpg'
        html,all_novel_name = get_htm(url)
        get_more_info(novel_id,all_novel_name,img_url,headers)
        ch_lis = get_novel_title(html)
    except (IndexError,AttributeError):
        version = 1
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        img_url = f'https://img.wenku8.com/image/{version}/{novel_id}/{novel_id}s.jpg'
        html,all_novel_name = get_htm(url)
        get_more_info(novel_id,all_novel_name,img_url,headers)
        ch_lis = get_novel_title(html)

    with tqdm(total=len(ch_lis)) as bar:
        async with aiohttp.ClientSession(headers=headers) as session:
            for item in ch_lis:
                ch_id,ch_name = item[0],item[1]
                pack_url = f'http://dl.wenku8.com/pack.php?aid={novel_id}&vid={int(ch_id)}'
                tasks.append(asyncio.create_task(pack_dl( pack_url, session,ch_name, all_novel_name, bar))) 
            await asyncio.wait(tasks)
    
    book_info['title_list'] = book_title_lis
    with open(f'novel/{all_novel_name}/book_info.json',mode='w',encoding='utf-8') as f:
        f.write(json.dumps(book_info,ensure_ascii=False))

if __name__ =='__main__':
    novel_id = int(input("id:")) # https://www.wenku8.net/novel/2/{id}/index.htm or https://www.wenku8.net/book/{id}.htm
    asyncio.run(main(novel_id))
    
    if epub_convert:
        convert_epub.main(book_info['book_title'])
