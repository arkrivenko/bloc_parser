import time
import requests
import csv
import json
from bs4 import BeautifulSoup
from security import SHOP_URL


headers = {
    'authority': SHOP_URL,
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'if-modified-since': 'Wed, 12 Jan 2011 15:04:36 GMT',
    'referer': f'https://{SHOP_URL}/',
    'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
}


def main():
    """
    Shop catalog parser that generates a json document for subsequent price updates
    (it uses the name of the product on the donor site and its ID assigned by our sales platform,
    which link the catalogs to each other)
    and the csv document for the initial unloading of goods on our platform
    """
    dict_bloc = {}
    with open("import_file.csv", "w", newline='', encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv, delimiter=";")
        titles_line = ["Корневая", "Подкатегория 1", "Название товара или услуги", "Цена продажи", "Краткое описание",
                       "Характеристики", "Изображения", "Остаток"]
        writer.writerow(titles_line)

    response = requests.get(f'https://{SHOP_URL}/catalog/', headers=headers)
    src = response.text
    soup = BeautifulSoup(src, "lxml")
    cat_table = soup.find(class_="seo-text").find_all("li")
    for cat in cat_table:
        cat_name = cat.find("a").text.strip()
        cat_href = f"https://{SHOP_URL}" + cat.find("a")["href"]
        print(f"\n{cat_name}: {cat_href}")
        cat_response = requests.get(cat_href, headers=headers)
        cat_src = cat_response.text
        cat_soup = BeautifulSoup(cat_src, "lxml")
        good_table = cat_soup.find(class_="b-c-catalog").find_all(class_="b-c-catalog-item")
        print(f"Всего товаров: {len(good_table)}\n")
        for good in good_table:
            good_href = f"https://{SHOP_URL}" + good.find(class_="b-c-catI-img").find("a")["href"]
            time.sleep(2)
            good_response = requests.get(good_href, headers=headers)
            good_src = good_response.text
            good_soup = BeautifulSoup(good_src, "lxml")
            item_dict = page_reader(good_soup, cat_name, good_href)
            if item_dict:
                dict_bloc.update(item_dict)

    with open("bloc_dict.json", "w", encoding="utf-8") as f_json:
        json.dump(dict_bloc, f_json, ensure_ascii=False, indent=4)


def page_reader(soup, cat_name: str, good_href: str):
    """
    Function for collecting the necessary attributes and parameters from the soup obtained from the product page

    :param soup: BeautifulSoup obj
    :param cat_name: category name (used for making csv)
    :param good_href: good's page url
    :return: item dict (title and edited price there)
    """
    item_dict = {}
    try:
        title = soup.find(class_="inner-text").find("h1").text.strip()
        price = soup.find(class_="c-i-l3-c-price").find("span").text.strip()
        if " " in price:
            price = price.replace(" ", "")
        edited_price = round((float(price) * 1.35), 2)
        image = f"https://{SHOP_URL}" + soup.find(class_="photo-cat-bg").find("a").find("img")["src"]
        short_desc = soup.find(class_="b-c-catI-h3")
        full_desc = soup.find(class_="cat-haracteristics")

        with open("import_file.csv", "a", newline='', encoding="utf-8") as f_csv:
            writer = csv.writer(f_csv, delimiter=";")
            titles_line = ["брусчатка, ПЛИТЫ, ступени, бордюр", cat_name, title, edited_price, short_desc,
                           full_desc, image, 100000]
            writer.writerow(titles_line)

        item_dict = {title: {
            "price": edited_price,
            "var_id": None
        }}
    except Exception as ex:
        print(f"{good_href}: {ex}")
    finally:
        return item_dict


def dict_maker():
    """
    The function of adding to the previously generated json document the product ID,
    obtained from the uploaded csv document from our site
    """
    ads = []
    with open("bloc_dict.json", encoding="utf-8") as f_dict:
        id_dict = json.load(f_dict)

    with open("shop_data.csv", encoding="utf-16") as f_csv:
        spamreader = csv.reader(f_csv, delimiter='\t')
        for row in spamreader:
            for i_name in id_dict:
                id_dict[i_name]["price"] = float(id_dict[i_name]["price"])
                if i_name in ads:
                    continue
                if i_name in row[0]:
                    ads.append(i_name)
                    ad_id = row[1]
                    id_dict[i_name]["var_id"] = ad_id

    with open("bloc_dict.json", "w", encoding="utf-8") as f:
        json.dump(id_dict, f, ensure_ascii=False, indent=4)


def bloc_price_updater():
    """
    Function to update prices for previously uploaded goods.
    """
    response = requests.get(f'https://{SHOP_URL}/catalog/', headers=headers)
    src = response.text
    soup = BeautifulSoup(src, "lxml")
    cat_table = soup.find(class_="seo-text").find_all("li")
    for cat in cat_table:
        cat_name = cat.find("a").text.strip()
        cat_href = f"https://{SHOP_URL}" + cat.find("a")["href"]
        print(f"\n{cat_name}: {cat_href}")
        cat_response = requests.get(cat_href, headers=headers)
        cat_src = cat_response.text
        cat_soup = BeautifulSoup(cat_src, "lxml")
        good_table = cat_soup.find(class_="b-c-catalog").find_all(class_="b-c-catalog-item")
        print(f"Всего товаров: {len(good_table)}\n")
        for good in good_table:
            good_name = good.find(class_="b-c-catI-img").find("a").find("img")["title"]
            good_price = good.find(class_="b-c-i3").text.strip()
            if " " in good_price:
                good_price = good_price.replace(" ", "")
            if "Р" in good_price:
                good_price = good_price.replace("Р", "")
            if "-" in good_price:
                good_price = good_price.replace("-", "")
            edited_price = round((float(good_price) * 1.35), 2)
            print(f"{good_name}: {good_price}, edited: {edited_price}")

            time.sleep(2)


if __name__ == "__main__":
    main()
    # dict_maker()
    # bloc_price_updater()
