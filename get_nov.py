#-*- coding: utf-8 -*
import json
import requests
import asyncio
import re
import aiofiles
import aiohttp
import os

from pprint import pprint
from tqdm import tqdm

dl_img = True
book_info = {}

def get_htm(url):
    req = requests.get(url)
    req.encoding = 'gbk'
    text = req.text
    all_novel_name = re.search(r'<div id="title">(?P<name>.*?)</div>',text,re.S) 
    find_author = re.search(r'<div id="info">作者：(?P<author>.*?)</div>',text,re.S) 
    nov_name = all_novel_name.group('name')
    author_name = find_author.group('author')

    book_info['book_title'] = nov_name
    book_info['book_author'] = author_name
    book_info['book_language'] = 'zh'
    book_info['book_identifier'] = url

    return text,nov_name,author_name

def get_more_info(nov_id,img_url,novel_name,headers):
    try:
        os.makedirs(f'novel/{novel_name}')
    except FileExistsError:
        pass
    
    url = f'https://www.wenku8.net/book/{nov_id}.htm'
    req = requests.get(url)
    req.encoding = 'gbk'
    text = req.text

    req_img = requests.get(img_url,headers=headers)
    with open(f'novel/{novel_name}/{img_url.split("/")[-1]}',mode='wb') as f:
        f.write(req_img.content)
        book_info['cover'] = f'novel/{novel_name}/{img_url.split("/")[-1]}'
    
    
    dc_compile = re.compile(r'\<span\sclass\=\"hottext\"\>内容简介\：\<\/span><br \/\>\<span\sstyle\=\"font-size\:\d+px\;\"\>(?P<dc>.*?)\<\/span\>',re.S)
    tg_compile = re.compile(r'\<span\sclass\=\"hottext\"\sstyle\=\"font\-size\:\d+px\;\"\>\<b\>(?P<tg>.*?)\<\/b>\<\/span\>\<br \/\>')
    res_dc = dc_compile.search(text)
    res_tg = tg_compile.finditer(text)

    dc_info = res_dc.group('dc')
    dc_info = dc_info.replace('\r\n','')
    book_info['description'] = dc_info
    
    temp_ = []
    for itr in res_tg:
        tg_info = itr.group('tg')
        temp_.append(tg_info)
    
    tg_ = "<br />".join(temp_)
    book_info['tg'] = tg_
    
        
def get_novel_title(html,novel_id,version):
    Temp_ = {}
    novel_title = {}
    Temp_lis = []
    html_list = html.split('vcss')
    
    if version == 2:
        novel_compile = re.compile(r'colspan=".*?" vid=".*?">(?P<novel_name>.*?)</td>\r\n',re.S)
    elif version == 1:
        novel_compile = re.compile(r'colspan=".*?">(?P<novel_name>.*?)</td>\r\n',re.S)
        
    title_compile = re.compile(r'<td class="ccss"><a href="(?P<url>.*?)">(?P<title_name>.*?)</a></td>',re.S)  
    
    
    for novel in html_list:
        
        res_novel = novel_compile.finditer(novel)
        res_title = title_compile.finditer(novel)
        
        for it in res_novel:
            title_list = []
            Temp_2 = {}
            count_ = 0
            novel_name = it.group('novel_name')
            if count_ == 0:
                Temp_2[count_] = novel_name
                count_ += 1
            
            for title in res_title:
                title_anme = title.group('title_name')
                title_url = title.group('url')
                title_list.append({title_anme:f'https://www.wenku8.net/novel/{version}/{novel_id}/{title_url}'})
                if name_replace(title_anme) == '插图':
                    Temp_2[count_] = [title_anme,f"novel/{book_info['book_title']}/{novel_name}/"]
                else:
                    Temp_2[count_] = [f"novel/{book_info['book_title']}/{novel_name}/{count_-1}.{name_replace(title_anme)}.txt",name_replace(title_anme)]
                count_ += 1
            
            novel_title[novel_name] = title_list # {'第五部 女神的化身I':[{'序章': 'https://xxx.com/123.htm'},...]}
            Temp_lis.append(Temp_2)
            
    book_info['title_list'] = Temp_lis
    return novel_title


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
        
    return text_list
        
async def get_img(url,file,all_novel_name,session):
    obj = re.compile(r'<div class="divimage"><a href="(?P<img_re>.*?)"  target="_blank">',re.S)
    
    async with session.get(url) as req:
        img_url = obj.finditer(await req.text())
        r = 0
        for it in img_url:
            real_img_url = it.group('img_re')
            img_name = real_img_url.split('/')[-1]
            async with session.get(real_img_url) as req2:
                async with aiofiles.open(f'novel/{all_novel_name}/{file}/{r}.{img_name}',mode='wb') as aiofile:
                    await aiofile.write(await req2.content.read())
            r += 1

async def dl_novel(file,url,name,session,all_novel_name,pbar):
    name = name_replace(name)
    try:
        if '插图' in name:
            if dl_img == True:
                await get_img(url,file,all_novel_name,session)
                pbar.update(1)
                return ''
        async with aiofiles.open(f'novel/{all_novel_name}/{file}/{name}.txt',mode='w',encoding='utf-8') as aiofile:
            async with session.get(url) as req:
                text = await req.text()
                text_list = get_novel_text(text)
                novel_text = '\n\n'.join(text_list)
                await aiofile.write(novel_text)
                pbar.update(1)
    
    except FileNotFoundError:
        make_dir(file,all_novel_name)
        if '插图' in name:
            if dl_img == True:
                await get_img(url,file,all_novel_name,session)
                pbar.update(1)
                return ''
        async with aiofiles.open(f'novel/{all_novel_name}/{file}/{name}.txt',mode='w',encoding='utf-8') as aiofile:
            async with session.get(url) as req:
                text = await req.text()
                text_list = get_novel_text(text)
                novel_text = '\n\n'.join(text_list)
                await aiofile.write(novel_text)
                pbar.update(1)
        

async def main(novel_id):
    tasks_long = 0
    tasks = []
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    try:
        version = 2
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        img_url = f'https://img.wenku8.com/image/{version}/{novel_id}/{novel_id}s.jpg'
        html,all_novel_name,author_name = get_htm(url)
        get_more_info(novel_id,img_url,all_novel_name,headers)
        novel_title = get_novel_title(html,novel_id,version)
    except (IndexError,AttributeError):
        version = 1
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        img_url = f'https://img.wenku8.com/image/{version}/{novel_id}/{novel_id}s.jpg'
        html,all_novel_name,author_name = get_htm(url)
        get_more_info(novel_id,img_url,all_novel_name,headers)
        novel_title = get_novel_title(html,novel_id,version)
    
    for key,valeue in novel_title.items():
        tasks_long = tasks_long + len(novel_title[key])
    with tqdm(total=tasks_long) as bar:
        async with aiohttp.ClientSession(headers=headers) as session:
            for key,valeue in novel_title.items():
                r = 0
                for dict in valeue:                    
                    for key_n,valeue_n in dict.items():
                        tasks.append(asyncio.create_task(dl_novel( key, valeue_n,f'{r}.{key_n}', session, all_novel_name, bar))) 
                    r += 1
            await asyncio.wait(tasks)
    
    with open(f'novel/{all_novel_name}/book_info.json',mode='w',encoding='utf-8') as f:
        f.write(json.dumps(book_info,ensure_ascii=False))

if __name__ =='__main__':
    novel_id = 2428 # https://www.wenku8.net/novel/2/{id}/index.htm or https://www.wenku8.net/book/{id}.htm
    asyncio.run(main(novel_id))
